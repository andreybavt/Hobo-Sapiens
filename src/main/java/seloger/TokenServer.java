package seloger;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import io.jsonwebtoken.Header;
import io.jsonwebtoken.JwtBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.apache.log4j.Logger;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;
import java.util.TimeZone;
import java.util.UUID;
import java.util.concurrent.Executors;

class TokenServer {
    static final Logger logger = Logger.getLogger("Server");

    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 8001), 0);

        server.createContext("/seloger-auth", new TokenServer.MyHttpHandler());
        server.setExecutor(Executors.newFixedThreadPool(3));
        server.start();
        logger.info(" Server started on port 8001");
    }

    public static class MyHttpHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            Map<String, Object> hashMap = new HashMap<>();
            hashMap.put("app", "63ee714d-a62a-4a27-9fbe-40b7a2c318e4");  //config.getAuthorizationCode());
            hashMap.put("iss", "SeLoger-mobile");  //config.getAuthorizationIssuer());
            hashMap.put("aud", "SeLoger-Mobile-6.0");  //config.getAuthorizationAudience());
            Calendar instance = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
            hashMap.put("iat", instance.getTimeInMillis() / ((long) 1000));
            String uuid = UUID.randomUUID().toString();
            hashMap.put("jti", uuid);
            JwtBuilder headerParam = Jwts.builder().setClaims(hashMap).setHeaderParam("typ", Header.JWT_TYPE);
            SignatureAlgorithm signatureAlgorithm = SignatureAlgorithm.HS256;
            String authorizationSecret = "b845ec9ab0834b5fb4f3a876295542887f559c7920224906bf4bc715dd9e56bc"; //config.getAuthorizationSecret();
            Charset charset = StandardCharsets.UTF_8;
            byte[] bytes = authorizationSecret.getBytes(charset);
            String compact = headerParam.signWith(signatureAlgorithm, bytes).compact();

            exchange.sendResponseHeaders(200, compact.length());
            OutputStream stream = exchange.getResponseBody();
            stream.write(compact.getBytes());
            stream.flush();
            stream.close();

        }
    }
}