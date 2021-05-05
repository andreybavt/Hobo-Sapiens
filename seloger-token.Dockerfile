FROM openjdk:15-alpine
EXPOSE 8001

WORKDIR /usr/src/app

COPY gradle gradle
COPY build.gradle .
COPY gradlew .
COPY settings.gradle .

COPY src/main/java src/main/java
COPY src/main/resources src/main/resources
RUN ./gradlew installDist

CMD ["./build/install/seloger-token-server/bin/seloger-token-server"]