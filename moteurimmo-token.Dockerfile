FROM node:8.6-alpine
EXPOSE 18081

WORKDIR /usr/src/app

RUN npm init -y && npm install object-hash
COPY src/main/javascript/moteurimmo/tokenserver.js .

CMD ["node", "tokenserver.js"]