FROM node:8.6-alpine
EXPOSE 18081

WORKDIR /usr/src/app

COPY src/main/javascript/moteurimmo/package.json .
COPY src/main/javascript/moteurimmo/tokenserver.js .
RUN npm install

CMD ["node", "tokenserver.js"]