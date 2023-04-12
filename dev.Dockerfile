FROM plone/plone-backend
COPY ../ /app/src/pas.plugins.oidc
RUN find /app/src/pas.plugins.oidc
RUN bin/pip install src/pas.plugins.oidc -c constraints.txt
