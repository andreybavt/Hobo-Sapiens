build:
	mvn clean install assembly:assembly

serve:
	java -jar target/seloger-token-server-jar-with-dependencies.jar