"use strict";

// Isolated publication artwork only: no game, transport, or model is exercised.
const fs = require("node:fs");
const { chromium } = require("playwright");
const config = JSON.parse(fs.readFileSync(0, "utf8"));

async function main() {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 1600 } });
    const results = [];
    for (const figure of config.figures) {
      await page.setContent(figure.svg.replace(/<\?xml[^>]*\?>/, ""));
      await page.locator("svg").evaluate((svg, width) => {
        svg.style.width = `${width}px`;
        svg.style.height = "auto";
        svg.style.display = "block";
      }, figure.width);
      await page.evaluate(() => document.fonts.ready);
      if (figure.mutation) {
        await page.locator("svg").evaluate((svg, mutation) => {
          const labels = svg.querySelectorAll("text");
          if (mutation === "undersized-font") {
            for (const label of labels) label.style.fontSize = "8px";
          } else if (mutation === "clipped-label") {
            labels[0].setAttribute("x", "0");
            labels[0].setAttribute("text-anchor", "start");
          } else if (mutation === "colliding-labels") {
            for (const key of ["x", "y", "text-anchor"])
              labels[1].setAttribute(key, labels[0].getAttribute(key));
          } else if (mutation === "colliding-lines") {
            const text = [...labels].find((label) => label.textContent.includes("model output"));
            text.querySelectorAll(":scope > tspan")[1].setAttribute("dy", "0");
          } else if (mutation === "rotated-shield-padding") {
            const text = [...labels].find((label) => label.textContent === "TRUST");
            const shield = text.parentElement.querySelector("rect");
            const gap = shield.getBoundingClientRect().right - text.getBoundingClientRect().right;
            const dx = (gap - 4) / svg.getScreenCTM().a;
            text.setAttribute("transform", `translate(${dx} 0) ${text.getAttribute("transform")}`);
          } else if (mutation === "flattened-subscripts") {
            for (const sub of svg.querySelectorAll('[baseline-shift="sub"]')) {
              sub.setAttribute("baseline-shift", "baseline");
              sub.setAttribute("font-size", "100%");
            }
          } else if (mutation === "raw-math-escape") {
            const text = [...labels].find((label) => label.textContent.includes("invalid:"));
            text.textContent = "invalid: \\rho";
          } else if (mutation === "ledger-arrow") {
            const line = [...svg.querySelectorAll("tspan")]
              .find((span) => span.textContent === "STAGE a>b");
            line.textContent = "STAGE a→b";
          } else if (mutation.startsWith("disclosure-") && mutation.endsWith("-padding")) {
            const role = mutation.split("-")[1];
            const text = svg.querySelector(`text.${{ header: "head", body: "cell", arm: "arm" }[role]}`);
            const origin = new DOMPoint(text.x.baseVal.getItem(0).value,
              text.y.baseVal.getItem(0).value).matrixTransform(text.getScreenCTM());
            const card = [...svg.querySelectorAll("rect")].map((rect) => rect.getBoundingClientRect())
              .filter((rect) => rect.left <= origin.x && rect.right >= origin.x &&
                rect.top <= origin.y && rect.bottom >= origin.y)
              .sort((a, b) => a.width * a.height - b.width * b.height)[0];
            const box = text.getBoundingClientRect();
            const dx = role === "header" ? card.right - box.right - 4 : card.left - box.left + 4;
            text.setAttribute("transform", `translate(${dx / svg.getScreenCTM().a} 0)`);
          } else if (mutation === "disclosure-small-line") {
            svg.querySelector("text.head tspan").style.fontSize = "8px";
          } else if (mutation === "disclosure-header-overlap") {
            svg.querySelector("text.head tspan[dy]").setAttribute("dy", "0");
          } else if (mutation === "disclosure-body-overlap") {
            const cell = svg.querySelector("g[data-arm][data-stratum]");
            const labels = cell.querySelectorAll("text");
            labels[2].setAttribute("transform",
              `translate(0 ${labels[1].y.baseVal.getItem(0).value - labels[2].y.baseVal.getItem(0).value})`);
          } else if (mutation.startsWith("disclosure-value-")) {
            const field = mutation.slice("disclosure-value-".length);
            const cell = svg.querySelector(`g[data-arm="${field === "NR" ? "unchecked_isolated" : "general_rule"}"][data-stratum="normal"]`);
            const line = [...cell.querySelectorAll("tspan, text")].find((node) =>
              !node.children.length && node.textContent.startsWith(field === "n" ? "n=" : `${field} `));
            line.textContent = field === "n" ? "n=0" : field === "NR" ? "NR 0" :
              line.textContent.replace(/(\d+)\/(\d+)/, "$2/$1");
          } else {
            throw new Error(`Unknown physical mutation: ${mutation}`);
          }
        }, figure.mutation);
      }
      results.push(await page.locator("svg").evaluate((svg) => {
        const matrix = svg.getScreenCTM();
        const bounds = (element, box = element.getBBox()) => {
          const transform = element.getScreenCTM();
          const points = [[box.x, box.y], [box.x + box.width, box.y],
            [box.x + box.width, box.y + box.height], [box.x, box.y + box.height]]
            .map(([x, y]) => new DOMPoint(x, y).matrixTransform(transform));
          return { left: Math.min(...points.map((point) => point.x)),
            top: Math.min(...points.map((point) => point.y)),
            right: Math.max(...points.map((point) => point.x)),
            bottom: Math.max(...points.map((point) => point.y)),
            points: points.map(({ x, y }) => ({ x, y })) };
        };
        const context = document.createElement("canvas").getContext("2d");
        const inkBounds = (line) => {
          // Font em-boxes can overlap while the actual subscript and next line do not.
          // Measure glyph ink at the SVG renderer's own baselines, then apply its CTM.
          const nodes = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
          const ink = [];
          let offset = 0;
          while (nodes.nextNode()) {
            const node = nodes.currentNode;
            const style = getComputedStyle(node.parentElement);
            context.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
            for (const char of node.textContent) {
              const start = line.getStartPositionOfChar(offset++);
              if (!char.trim()) continue;
              const metric = context.measureText(char);
              ink.push(bounds(line, { x: start.x - metric.actualBoundingBoxLeft,
                y: start.y - metric.actualBoundingBoxAscent,
                width: metric.actualBoundingBoxLeft + metric.actualBoundingBoxRight,
                height: metric.actualBoundingBoxAscent + metric.actualBoundingBoxDescent }));
            }
          }
          if (!ink.length) throw new Error("Cannot measure an empty visible line");
          return { left: Math.min(...ink.map((box) => box.left)),
            top: Math.min(...ink.map((box) => box.top)),
            right: Math.max(...ink.map((box) => box.right)),
            bottom: Math.max(...ink.map((box) => box.bottom)) };
        };
        const rects = [...svg.querySelectorAll("rect")].map((rect) => ({
          ...bounds(rect), fill: getComputedStyle(rect).fill,
          shield: rect.classList.contains("label-shield"), element: rect,
        }));
        const texts = [...svg.querySelectorAll("text")].filter((text) =>
          text.textContent.trim() && getComputedStyle(text).visibility !== "hidden"
        ).map((text) => {
          const transform = text.getScreenCTM();
          const origin = new DOMPoint(text.x.baseVal.getItem(0).value,
            text.y.baseVal.getItem(0).value).matrixTransform(transform);
          const containing = rects.filter((rect) => {
            const local = origin.matrixTransform(rect.element.getScreenCTM().inverse());
            const box = rect.element.getBBox();
            return local.x >= box.x && local.x <= box.x + box.width &&
              local.y >= box.y && local.y <= box.y + box.height &&
              // White label shields are content containers, unlike the white canvas.
              rect.bottom - rect.top >= 25 &&
              (rect.shield || rect.fill !== "rgb(255, 255, 255)");
          }).sort((a, b) => (a.right - a.left) * (a.bottom - a.top) -
            (b.right - b.left) * (b.bottom - b.top));
          const card = containing[0];
          const measured = bounds(text);
          const insets = card ? card.points.map((start, index) => {
            const end = card.points[(index + 1) % card.points.length];
            return Math.min(...measured.points.map((point) =>
              ((end.x - start.x) * (point.y - start.y) -
               (end.y - start.y) * (point.x - start.x)) /
              Math.hypot(end.x - start.x, end.y - start.y)));
          }) : null;
          const group = text.closest("g[data-arm][data-stratum]");
          const inkLines = [...text.children].filter((line) => line.localName === "tspan");
          return { text: text.textContent.trim(), ...measured,
            lines: [...text.children].filter((line) =>
              line.localName === "tspan" && line.hasAttribute("x")
            ).map((line) => ({ text: line.textContent.trim(), ...inkBounds(line) })),
            fontSize: parseFloat(getComputedStyle(text).fontSize) * Math.hypot(transform.a, transform.b),
            card: card ? { left: card.left, top: card.top, right: card.right,
              bottom: card.bottom, shield: card.shield } : null,
            insets,
            role: text.getAttribute("class"),
            cell: group ? { arm: group.dataset.arm, stratum: group.dataset.stratum } : null,
            inkLines: (svg.dataset.paperLabel === "fig:disclosure-signals" ?
              (inkLines.length ? inkLines : [text]) : []).map((line) => ({
              text: line.textContent.trim(), ...inkBounds(line),
              fontSize: parseFloat(getComputedStyle(line).fontSize) *
                Math.hypot(line.getScreenCTM().a, line.getScreenCTM().b),
            })),
            // SVG collapses source indentation; index its rendered character stream.
            glyphs: Array.from({ length: text.getNumberOfChars() }, (_, index) => ({
              char: text.textContent.replace(/\s+/g, " ").trim()[index],
              ...bounds(text, text.getExtentOfChar(index)),
            })) };
        });
        const view = svg.viewBox.baseVal;
        const corner = new DOMPoint(view.x, view.y).matrixTransform(matrix);
        return { canvas: { left: corner.x, top: corner.y,
          right: corner.x + view.width * matrix.a, bottom: corner.y + view.height * matrix.d }, texts };
      }));
    }
    process.stdout.write(JSON.stringify(results));
  } finally {
    await browser.close();
  }
}
main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
