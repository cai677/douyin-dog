# Content Classification Reference

Use a single primary content type for each clip. If a clip could fit multiple types, choose the type that dominates the visual action, not the subtitle text.

## Default Categories

| Key | Chinese folder | Use for |
|---|---|---|
| `person_talking` | `人物口播-医生讲解` | Person, vet, expert, or seller talking to camera. Product may be held, but the person is the main subject. |
| `pet_eye_symptom` | `宠物眼部症状-特写` | Eye discharge, tear stains, redness, swelling, dirty eye corners, symptom montages. |
| `eye_exam_cleaning` | `眼部检查-擦拭-清洁` | Wiping, checking, flipping eyelids, cleaning around the eye, grooming related to eye care. |
| `eye_drop_demo` | `滴眼-上药使用演示` | Dropper or medicine applied to the pet eye; bottle tip near the eye is enough when the action is clearly use. |
| `product_closeup` | `产品包装-瓶身-空镜` | Bottle, box, packaging, product held alone, or product staged as the visual focus. |
| `proof_product` | `资质报告-成分-pH-背书` | Test reports, pH cards, ingredient sheets, official approval/兽药字/国标/监管 proof. |
| `result_pet_scene` | `宠物状态-效果展示` | Healthy/relieved pet state, normal tears, before-after/result emphasis, non-operation pet life scene. |
| `price_purchase` | `价格-购买-支付画面` | Price screenshots, payment screens, order cues, buying/stocking instructions. |
| `other_transition` | `过渡-其他` | Transitions, unusable fragments, or scenes that do not fit the above. |

## Practical Rules

- Prefer stable, human-readable Chinese folders for final browsing.
- Keep the original split clips intact; classification should copy files into category folders unless the user asks to move them.
- Use `视频名_片段名.mp4` as the copied filename so `A01` from different videos never collides.
- Keep `classified_index.csv` with source video, segment id, time range, content type, source path, and classified path.
- For a new product category, extend the category map only when the existing categories force too many clips into `other_transition`.
