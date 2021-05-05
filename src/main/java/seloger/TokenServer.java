package seloger;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.apache.log4j.Logger;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;

import static seloger.NewTokenGenerator.generateToken;


class TokenServer {
    static final Logger logger = Logger.getLogger("Server");

    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", 8001), 0);

        server.createContext("/seloger-auth", new TokenServer.MyHttpHandler());
        server.setExecutor(Executors.newFixedThreadPool(3));
        server.start();
        logger.info(" Server started on port 8001");
    }

    public static class MyHttpHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            OutputStream stream = exchange.getResponseBody();
            try {
                String decode = URLDecoder.decode(exchange.getRequestURI().getRawQuery(), "UTF-8");
                Map<String, String> args = new HashMap<>();
                for (String kv : decode.split("&")) {
                    String[] kvArr = kv.split("=");
                    args.put(kvArr[0], kvArr[1]);
                }
                String compact = generateToken(args.get("encryption"), Integer.parseInt(args.get("expirationDate")), args.get("salt"));
                exchange.sendResponseHeaders(200, compact.length());
                stream.write(compact.getBytes());
            } catch (Exception e) {
                e.printStackTrace();
                exchange.sendResponseHeaders(500, 0);
            }
            stream.flush();
            stream.close();
        }
    }


}