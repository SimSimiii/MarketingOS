# Browser session correction — 14 October 2026

Reproduced in the production browser: successful sign-in returned immediately to `/login/?next=%2F`. Direct API tests had passed because they called the console origin or explicitly supplied the bearer token, so they had not exercised the deployed browser routing.

Root cause: CodeBuild project `marketingos-build-console-prod` had `NEXT_PUBLIC_API_URL` set to the absolute API Gateway URL. Browser auth uses `credentials: same-origin` and reads the access cookie on the console origin; calling a different origin cannot establish that session.

Correction: changed the project setting to `/api`, preserved other environment settings, and made `frontend/buildspec.yml` require exactly `/api`. Commit `7cff9148eb7497025fa26e2775fa9bb583836382`. Console build `marketingos-build-console-prod:6445b7f5-4a36-45c2-a1de-6942185b4553` succeeded, including lint, typecheck and frontend tests.

Verification: actual production-browser sign-in reaches the dashboard, navigation to Brands works, and reloading that page keeps the session. The sidebar shows Mehdi and 0/50 runs. Evidence: `session-fixed-production.jpg`. The account quota was raised from five to 50 without changing its normal user role or password, with an atomic IAM-provisioning audit record; temporary Lambda removed.

Tester instructions are now `tester-guide.en.md` and cover e-commerce, SaaS and affiliate/other offers. The previous French copy test remains a historical case, not the new tester scenario.
