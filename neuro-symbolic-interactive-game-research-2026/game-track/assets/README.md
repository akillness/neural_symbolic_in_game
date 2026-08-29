# Public-safe asset boundary / 공개 안전 자산 경계

This latest-only public snapshot intentionally contains no generated concept PNGs. The omitted
SL-C01–SL-C04, rejected SL-C04 v1, and SL3D candidates remain subject to human rights/style review
and are therefore neither runtime-eligible nor publication-eligible.

[`concepts/public-exclusion.json`](concepts/public-exclusion.json) records every omitted byte
stream by stable ID, relative filename, and SHA-256. The validator fails if an omitted PNG appears
in this tree or if the exclusion set drifts. This exclusion applies to the pending concept lane,
not to separately curated runtime assets. The public playable uses curated Higgsfield UI files and
the validated tracked Higgsfield player GLB under `../godot/assets/`, plus procedural world/VFX,
generated PCM audio, and the separately licensed Nanum Gothic font. Player visuals and animation
remain presentation-only.

이 최신 전용 공개 스냅샷에는 생성형 콘셉트 PNG를 의도적으로 포함하지 않는다. 제외한
SL-C01–SL-C04, 거부된 SL-C04 v1, SL3D 후보는 인간 권리·스타일 검토 전이므로 런타임 및
공개 배포 자격이 없다. [`concepts/public-exclusion.json`](concepts/public-exclusion.json)은
제외 바이트를 ID·상대 경로·SHA-256으로 고정하며, PNG가 다시 나타나거나 목록이 달라지면
검증이 실패한다. 이 제외 규칙은 검토 대기 콘셉트 lane에만 적용된다. 공개 플레이어블은
`../godot/assets/` 아래 별도 큐레이션 Higgsfield UI와 검증된 추적 플레이어 GLB를 절차 월드·
VFX·생성 PCM 음향·별도 라이선스 Nanum Gothic 글꼴과 함께 사용한다. 플레이어 외형과
애니메이션은 프레젠테이션 전용이다.
