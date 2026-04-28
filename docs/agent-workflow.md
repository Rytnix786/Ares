+# Agent-Assisted Development in Ares
+
+This repo was built with AI agent assistance. Here's how we use agents effectively for Ares development.
+
+## Skills Used
+
+| Skill | When to Use | When NOT to Use |
+|-------|-------------|-----------------|
+| backend-dev-guidelines | API/service work | Frontend tasks |
+| frontend-ui-engineering | Dashboard work | Backend tasks |
+| api-and-interface-design | Schema/contract work | Already-stable APIs |
+| ci-cd-and-automation | Workflow/Docker work | Application code |
+| documentation-templates | Docs and README | Implementation |
+| verification-before-completion | Before any milestone close | Early drafts |
+
+## Sub-Agent Roles
+
+| Agent | Owns | Never Touches |
+|-------|------|---------------|
+| Docs agent | README, docs/, CHANGELOG | ares/, docker-compose |
+| Backend agent | ares/api/, ares/db/, ares/gate/ | dashboard/, README |
+| Dashboard agent | dashboard/ | ares/, docker-compose |
+| CI/DevEx agent | Makefile, .github/, docker-compose*.yml | ares/, dashboard/ |
+
+## Validation Rules
+
+Every agent output must include:
+
+- Files changed
+- Commands run with output
+- Evidence of passing verification