FROM grafana/grafana
# Disable Login form or not
# ENV GF_AUTH_DISABLE_LOGIN_FORM="true"
# # Allow anonymous authentication or not
# ENV GF_AUTH_ANONYMOUS_ENABLED="true"
# # Role of anonymous user
# ENV GF_AUTH_ANONYMOUS_ORG_ROLE="Admin"
ENV GF_DATABASE_SSL_MODE="disable"
ENV GF_SERVER_PROTOCOL="https"
ENV GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH="/etc/grafana/dashboards/aggregates.json"

ADD ./provisioning /etc/grafana/provisioning
ADD ./dashboards /etc/grafana/dashboards
