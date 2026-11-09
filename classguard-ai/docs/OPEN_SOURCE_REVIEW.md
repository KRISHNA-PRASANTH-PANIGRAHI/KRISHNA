# ClassGuard AI — Open-source reference review

Review date: **2026-11-03**

This records observed upstream license metadata, source purpose, and reuse boundaries. It is a planning review, not an approval to import code. No upstream application was installed, executed, or copied into ClassGuard. The supplied PRD PDF remains unchanged.

## Established references

| Reference | Observed root license | Relevant use and boundary |
| --- | --- | --- |
| [LiveKit Meet](https://github.com/livekit-examples/meet) | [Apache-2.0](https://github.com/livekit-examples/meet/blob/main/LICENSE) | Next.js conferencing reference using LiveKit Components. Useful prejoin, device controls, and meeting UI; requires a configured LiveKit service. |
| [LiveKit Components JS](https://github.com/livekit/components-js) | [Apache-2.0](https://github.com/livekit/components-js/blob/main/LICENSE) | Official React components for LiveKit Cloud or a self-hosted server. Includes an upstream NOTICE file. Candidate UI foundation. |
| [LiveKit Server](https://github.com/livekit/livekit) | [Apache-2.0](https://github.com/livekit/livekit/blob/master/LICENSE) | WebRTC media server/SFU. Candidate conferencing infrastructure; classroom identity, enrolment, attendance rules, and records remain application work. |
| [BigBlueButton](https://github.com/bigbluebutton/bigbluebutton) | [LGPL-3.0](https://github.com/bigbluebutton/bigbluebutton/blob/v4.0.x-develop/LICENSE) | Complete classroom reference: polls, shared notes, whiteboards, breakout rooms, and learning analytics. Review component and distribution requirements before copying or modifying source. |
| [Jitsi Meet](https://github.com/jitsi/jitsi-meet) | [Apache-2.0](https://github.com/jitsi/jitsi-meet/blob/master/LICENSE) | Conferencing application and integration reference. Its source license is separate from hosted-service terms: public meet.jit.si embedding is for testing, not production. See [official service guidance](https://jitsi.org/api/). |
| [MediaPipe](https://github.com/google-ai-edge/mediapipe) | [Apache-2.0](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE) | On-device ML toolkit, not a complete attendance product. Face Landmarker outputs landmarks, blendshapes, and transforms; these outputs do not establish identity, comprehension, or misconduct. See [task documentation](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js). |

These are root-license observations, not a blanket finding about every dependency, bundled asset, model, or hosted service. Record the exact revision, applicable license/NOTICE files, modifications, and separately sourced model terms before adoption.

## Exact PRD references

The supplied PRD identifies **Yuga-04/AI-Classroom-Monitor**. It replaces the earlier name-only search candidate `Manuja-15/ai-classroom-monitor`; that other repository is not the PRD reference.

| Repository and reviewed revision | Observed license metadata | Purpose and review status |
| --- | --- | --- |
| [Yuga-04/AI-Classroom-Monitor](https://github.com/Yuga-04/AI-Classroom-Monitor/tree/2d4861e2f3927daf9d2823c086640b1eb95d19ea), default branch `yugu`, commit `2d4861e2f3927daf9d2823c086640b1eb95d19ea` | No named license in inspected README; root `LICENSE` on `yugu` returned 404; GitHub license metadata was null. | Flask/SocketIO and SQLite monitoring prototype with local camera capture, face enrolment, reports, and heuristic analysis. Reference-only pending an explicit reuse-license review. |
| [Sumant3086/ProxyMukt-Attendance-System-](https://github.com/Sumant3086/ProxyMukt-Attendance-System-/tree/85b63eab622bfed827bbc4388bfe57fe39ddade4), branch `main`, commit `85b63eab622bfed827bbc4388bfe57fe39ddade4` | MIT stated and reproduced in README; linked root `LICENSE` returned 404; GitHub license metadata was null. | MERN attendance project describing QR tokens, geofencing, liveness, and reports. Record as **MIT stated in README; standalone license and provenance review pending**. No fraud-prevention accuracy claim has been validated. |
| [reevon-dsouza/AI-Assisted-classroom-monitoring](https://github.com/reevon-dsouza/AI-Assisted-classroom-monitoring/tree/df58e53ffa565b97f215ee51a572a98f83254e22), branch `main`, commit `df58e53ffa565b97f215ee51a572a98f83254e22` | README refers to unspecified repository license configuration; root `LICENSE` returned 404; GitHub license metadata was null. | YOLO/ArcFace/FastAPI classroom-video analysis prototype. Required custom model weights and face database are excluded from the repository. Reference-only until code and model reuse terms are established. |

Null GitHub metadata and a missing root file are observations, not conclusions about all possible permissions. Resolve the applicable license from the actual rights holder before importing uncertain material.

## Yuga-04 source inspection

Inspected the [README](https://github.com/Yuga-04/AI-Classroom-Monitor/blob/2d4861e2f3927daf9d2823c086640b1eb95d19ea/README.md), [requirements](https://github.com/Yuga-04/AI-Classroom-Monitor/blob/2d4861e2f3927daf9d2823c086640b1eb95d19ea/requirements.txt), [Flask application](https://github.com/Yuga-04/AI-Classroom-Monitor/blob/2d4861e2f3927daf9d2823c086640b1eb95d19ea/backend/app.py), [video processor](https://github.com/Yuga-04/AI-Classroom-Monitor/blob/2d4861e2f3927daf9d2823c086640b1eb95d19ea/backend/modules/video_processor.py), and [configuration](https://github.com/Yuga-04/AI-Classroom-Monitor/blob/2d4861e2f3927daf9d2823c086640b1eb95d19ea/backend/config.py).

- The processor opens a webcam/IP-camera source with OpenCV and emits annotated frames through SocketIO. This is a monitoring pipeline, not a multiparty WebRTC classroom service.
- The application contains demonstration authentication/configuration patterns. It has not received a complete security or production-readiness review.
- The README's engagement and cheating labels use facial/emotion and pose heuristics. Their presence in source is not evidence of educational validity or detection accuracy. They are not adopted as ClassGuard requirements by this review.
- Dependencies use broad version ranges and models may download on first use. Dependency compatibility, model provenance, and redistribution terms need separate checks before any adoption.

## Adoption record required

For each selected component, record the pinned commit/version, files reused, applicable license and notices, dependency/model inventory, and validation performed. Keep the three PRD prototypes as research references until those entries are complete. No implementation or dependency installation is authorized by this document itself.
