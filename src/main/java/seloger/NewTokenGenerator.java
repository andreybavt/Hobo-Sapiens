package seloger;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.json.JSONObject;

import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.security.spec.InvalidKeySpecException;
import java.util.*;


public class NewTokenGenerator {
    public static String generateToken(String encryption, int expirationDate, String salt) throws Exception {
        Map<String, Object> hashMap = createMapOfProps(encryption, expirationDate, salt);

        byte[] iconBytes = Objects.requireNonNull(NewTokenGenerator.class.getClassLoader().getResourceAsStream("sl-favicon.ico")).readAllBytes();
        String b64str = new String(Base64.getEncoder().encode(iconBytes));
        byte[] lastIconBytes = b64str.substring(b64str.length() - 128).getBytes(StandardCharsets.UTF_8);

        JwtBuilder jwtBuilder = Jwts.builder().setClaims(hashMap)
                .setIssuer("Mobile")
                .setAudience("V6_ua")
                .setSubject("123479")
                .setHeaderParam(Header.TYPE, Header.JWT_TYPE);
        jwtBuilder.signWith(Keys.hmacShaKeyFor(lastIconBytes), SignatureAlgorithm.HS256);
        return jwtBuilder.compact();
    }
    private static String oldGenerateToken() {
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
        return headerParam.signWith(signatureAlgorithm, bytes).compact();
    }

    public static String basicAppProps() {
        Map<String, Object> linkedHashMap = new LinkedHashMap<>();
        linkedHashMap.put("app", "SeLoger");
        linkedHashMap.put("platform", "Android");
        linkedHashMap.put("version", "6.4.7");
        linkedHashMap.put("osVersion", "29");
        return new JSONObject(linkedHashMap).toString();
    }

    // Props are from the first HTTP call
    public static Map<String, Object> createMapOfProps(String encryption, long expirationDate, String salt) throws Exception {
        String a = basicAppProps(); // json with {app platform version osVersion}
        UUID randomUUID = UUID.randomUUID();
        byte[] slt = createSalt(randomUUID);
        SecretKey b = makeSecretKey(slt, "Saucisse");
        byte[] a3 = random16bytes(); // random bytes ???
        String b2 = normalToHexString(encryptString(a, b, a3));
        String b3 = normalToHexString(a3);

        Map<String, Object> ret = new HashMap<>();
        ret.put("cha", encryption); // encryption
        ret.put(Claims.EXPIRATION, String.valueOf(expirationDate)); //expiration date
        ret.put("pep", salt); // salt
        ret.put("slt", normalToHexString(slt)); // based on uuid + Saucisse
        ret.put("data", b3 + ':' + b2);
        return ret;
    }

    public static String normalToHexString(byte[] bytes) {
        char[] HEX_ARRAY = "0123456789ABCDEF".toCharArray();
        char[] hexChars = new char[bytes.length * 2];
        for (int j = 0; j < bytes.length; j++) {
            int v = bytes[j] & 0xFF;
            hexChars[j * 2] = HEX_ARRAY[v >>> 4];
            hexChars[j * 2 + 1] = HEX_ARRAY[v & 0x0F];
        }
        return new String(hexChars).toLowerCase();
    }

    public static SecretKey makeSecretKey(byte[] salt, String password) throws InvalidKeySpecException {
        PBEKeySpec keySpec = new PBEKeySpec(password.toCharArray(), salt, 10000, 256);
        return new SelogerPBEKey(keySpec, "HmacSHA512");

    }

    public static byte[] createSalt(UUID uuid) {
        ByteBuffer order = ByteBuffer.wrap(new byte[16]).order(ByteOrder.BIG_ENDIAN);
        order.putLong(uuid.getMostSignificantBits());
        order.putLong(uuid.getLeastSignificantBits());
        return order.array();
    }

    public static byte[] random16bytes() {
        byte[] bArr = new byte[16];
        new SecureRandom().nextBytes(bArr);
        return bArr;
    }

    public static byte[] encryptString(String strToEncrypt, SecretKey secretKey, byte[] iv) throws Exception {
        IvParameterSpec ivParameterSpec = new IvParameterSpec(iv);
        javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(1, new SecretKeySpec(secretKey.getEncoded(), "AES"), ivParameterSpec);
        Charset forName = StandardCharsets.UTF_8;
        byte[] bytes = strToEncrypt.getBytes(forName);
        return cipher.doFinal(bytes);
    }
}
