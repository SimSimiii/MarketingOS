#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  MarketingOS - the secrets every other stack reads, as SSM SecureStrings.
#
#      ENV=prod bash iac/parameters.sh
#
#  Parameter Store rather than Secrets Manager: standard SecureString
#  parameters cost nothing, and eight secrets at $0.40 each were the largest
#  line on the bill after RDS. What is lost is rotation, which nothing here
#  uses - two of these must never rotate at all.
#
#  CloudFormation cannot create a SecureString, hence a script. It is
#  idempotent and, above all, never overwrites: a parameter that exists is
#  left exactly as it is. That is the property the whole file is built
#  around, because PASSWORD_PEPPER and ADMIN_PWD_PEPPER are folded into every
#  password hash - regenerating either makes every password in the database
#  permanently unverifiable.
#
#  Three values cannot be generated and start as placeholders:
#    database-url       written once database.yaml reports its endpoint
#    anthropic-api-key  only the vendor can mint these; set them by hand with
#    openai-api-key     aws ssm put-parameter --overwrite --type SecureString
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ENV="${ENV:-dev}"
PREFIX="/marketingos/${ENV}"

put_if_absent() {
  local name="$1" value="$2" description="$3"
  if aws ssm get-parameter --name "${PREFIX}/${name}" >/dev/null 2>&1; then
    echo "kept     ${PREFIX}/${name}"
  else
    aws ssm put-parameter --name "${PREFIX}/${name}" --type SecureString \
      --value "${value}" --description "${description}" >/dev/null
    echo "created  ${PREFIX}/${name}"
  fi
}

# Hex only: RDS rejects '/', '@', '"' and spaces in a master password, and a
# URL-encoding surprise inside DATABASE_URL is a bad way to learn that.
put_if_absent db-password      "$(openssl rand -hex 16)" "RDS master password. Read by database.yaml."
put_if_absent jwt-secret       "$(openssl rand -hex 32)" "Signs platform tokens. Rotating it signs everybody out."
put_if_absent password-pepper  "$(openssl rand -hex 32)" "PERMANENT. Folded into every platform password hash. Never replace."
put_if_absent admin-jwt-secret "$(openssl rand -hex 32)" "Signs operator tokens. Must differ from jwt-secret."
put_if_absent admin-pwd-pepper "$(openssl rand -hex 32)" "PERMANENT. Folded into every operator password hash. Never replace."
put_if_absent anthropic-api-key "unset" "Per-token billing for the campaign state machine. Set by hand."
put_if_absent openai-api-key    "unset" "The same, for the GPT half of the catalog. Set by hand."
put_if_absent database-url "postgresql+psycopg://set-me-after-the-database-stack" \
  "Full SQLAlchemy URL. Written once database.yaml reports its endpoint."
