# syntax=docker/dockerfile:1
ARG KEYCLOAK_VERSION
FROM quay.io/keycloak/keycloak:$KEYCLOAK_VERSION as builder

# Configure postgres database vendor
ENV KC_DB=postgres

# Disable health and metrics support
ENV KC_HEALTH_ENABLED=false
ENV KC_METRICS_ENABLED=false

# Enable features
ENV KC_FEATURES="token-exchange,scripts,preview,admin_fine_grained_authz"

WORKDIR /opt/keycloak

# Build
RUN /opt/keycloak/bin/kc.sh build --cache=ispn

FROM quay.io/keycloak/keycloak:$KEYCLOAK_VERSION
LABEL image.version=$KEYCLOAK_VERSION
COPY --from=builder /opt/keycloak/ /opt/keycloak/

USER root
RUN sed -i '/disabledAlgorithms/ s/ SHA1,//' /etc/crypto-policies/back-ends/java.config
USER keycloak

RUN /opt/keycloak/bin/kc.sh show-config

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
