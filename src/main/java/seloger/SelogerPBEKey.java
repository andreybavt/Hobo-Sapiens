package seloger;


import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.interfaces.PBEKey;
import javax.crypto.spec.PBEKeySpec;
import java.io.ObjectStreamException;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyRep;
import java.security.NoSuchAlgorithmException;
import java.security.spec.InvalidKeySpecException;
import java.util.Arrays;
import java.util.Locale;

/* access modifiers changed from: package-private */
public final class SelogerPBEKey implements PBEKey {

    /* renamed from: f  reason: collision with root package name */
    private char[] f2820f;

    /* renamed from: g  reason: collision with root package name */
    private byte[] f2821g;

    /* renamed from: h  reason: collision with root package name */
    private int f2822h;

    /* renamed from: i  reason: collision with root package name */
    private byte[] f2823i;

    /* renamed from: j  reason: collision with root package name */
    private Mac f2824j;

    /* access modifiers changed from: package-private */
    public static class a implements SecretKey {

        /* renamed from: f  reason: collision with root package name */
        final /* synthetic */ Mac f2825f;

        /* renamed from: g  reason: collision with root package name */
        final /* synthetic */ byte[] f2826g;

        a(Mac mac, byte[] bArr) {
            this.f2825f = mac;
            this.f2826g = bArr;
        }

        public boolean equals(Object obj) {
            if (this == obj) {
                return true;
            }
            if (a.class != obj.getClass()) {
                return false;
            }
            SecretKey secretKey = (SecretKey) obj;
            if (!this.f2825f.getAlgorithm().equalsIgnoreCase(secretKey.getAlgorithm()) || !Arrays.equals(this.f2826g, secretKey.getEncoded())) {
                return false;
            }
            return true;
        }

        public String getAlgorithm() {
            return this.f2825f.getAlgorithm();
        }

        public byte[] getEncoded() {
            return this.f2826g;
        }

        public String getFormat() {
            return "RAW";
        }

        public int hashCode() {
            return (Arrays.hashCode(this.f2826g) * 41) + this.f2825f.getAlgorithm().toLowerCase(Locale.ENGLISH).hashCode();
        }
    }

    SelogerPBEKey(PBEKeySpec pBEKeySpec, String str) throws InvalidKeySpecException {
        char[] password = pBEKeySpec.getPassword();
        if (password == null) {
            this.f2820f = new char[0];
        } else {
            this.f2820f = (char[]) password.clone();
        }
        byte[] b = b(this.f2820f);
        byte[] salt = pBEKeySpec.getSalt();
        this.f2821g = salt;
        if (salt != null) {
            int iterationCount = pBEKeySpec.getIterationCount();
            this.f2822h = iterationCount;
            if (iterationCount == 0) {
                throw new InvalidKeySpecException("Iteration count not found");
            } else if (iterationCount >= 0) {
                int keyLength = pBEKeySpec.getKeyLength();
                if (keyLength == 0) {
                    throw new InvalidKeySpecException("Key length not found");
                } else if (keyLength >= 0) {
                    try {
                        Mac instance = Mac.getInstance(str);
                        this.f2824j = instance;
                        this.f2823i = a(instance, b, this.f2821g, this.f2822h, keyLength);
                    } catch (NoSuchAlgorithmException e) {
                        InvalidKeySpecException invalidKeySpecException = new InvalidKeySpecException();
                        invalidKeySpecException.initCause(e);
                        throw invalidKeySpecException;
                    }
                } else {
                    throw new InvalidKeySpecException("Key length is negative");
                }
            } else {
                throw new InvalidKeySpecException("Iteration count is negative");
            }
        } else {
            throw new InvalidKeySpecException("Salt not found");
        }
    }

    private static byte[] a(Mac mac, byte[] bArr, byte[] bArr2, int i2, int i3) {
        int i4 = i3 / 8;
        byte[] bArr3 = new byte[i4];
        try {
            int macLength = mac.getMacLength();
            int i5 = ((i4 + macLength) - 1) / macLength;
            int i6 = i4 - ((i5 - 1) * macLength);
            byte[] bArr4 = new byte[macLength];
            byte[] bArr5 = new byte[macLength];
            mac.init(new a(mac, bArr));
            byte[] bArr6 = new byte[4];
            for (int i7 = 1; i7 <= i5; i7++) {
                mac.update(bArr2);
                bArr6[3] = (byte) i7;
                bArr6[2] = (byte) ((i7 >> 8) & 255);
                bArr6[1] = (byte) ((i7 >> 16) & 255);
                bArr6[0] = (byte) ((i7 >> 24) & 255);
                mac.update(bArr6);
                mac.doFinal(bArr4, 0);
                System.arraycopy(bArr4, 0, bArr5, 0, macLength);
                for (int i8 = 2; i8 <= i2; i8++) {
                    mac.update(bArr4);
                    mac.doFinal(bArr4, 0);
                    for (int i9 = 0; i9 < macLength; i9++) {
                        bArr5[i9] = (byte) (bArr5[i9] ^ bArr4[i9]);
                    }
                }
                if (i7 == i5) {
                    System.arraycopy(bArr5, 0, bArr3, (i7 - 1) * macLength, i6);
                } else {
                    System.arraycopy(bArr5, 0, bArr3, (i7 - 1) * macLength, macLength);
                }
            }
            return bArr3;
        } catch (GeneralSecurityException unused) {
            throw new RuntimeException("Error deriving PBKDF2 keys");
        }
    }

    private static byte[] b(char[] cArr) {
        ByteBuffer encode = StandardCharsets.UTF_8.encode(CharBuffer.wrap(cArr));
        int limit = encode.limit();
        byte[] bArr = new byte[limit];
        encode.get(bArr, 0, limit);
        return bArr;
    }

    private Object writeReplace() throws ObjectStreamException {
        return new KeyRep(KeyRep.Type.SECRET, getAlgorithm(), getFormat(), getEncoded());
    }

    public boolean equals(Object obj) {
        if (obj == this) {
            return true;
        }
        if (!(obj instanceof SecretKey)) {
            return false;
        }
        SecretKey secretKey = (SecretKey) obj;
        if (!secretKey.getAlgorithm().equalsIgnoreCase(getAlgorithm()) || !secretKey.getFormat().equalsIgnoreCase("RAW")) {
            return false;
        }
        byte[] encoded = secretKey.getEncoded();
        boolean equals = Arrays.equals(this.f2823i, secretKey.getEncoded());
        Arrays.fill(encoded, (byte) 0);
        return equals;
    }

    /* access modifiers changed from: protected */
    @Override // java.lang.Object
    public void finalize() throws Throwable {
        try {
            char[] cArr = this.f2820f;
            if (cArr != null) {
                Arrays.fill(cArr, '0');
                this.f2820f = null;
            }
            byte[] bArr = this.f2823i;
            if (bArr != null) {
                Arrays.fill(bArr, (byte) 0);
                this.f2823i = null;
            }
        } finally {
            super.finalize();
        }
    }

    public String getAlgorithm() {
        return "PBKDF2With" + this.f2824j.getAlgorithm();
    }

    public byte[] getEncoded() {
        return (byte[]) this.f2823i.clone();
    }

    public String getFormat() {
        return "RAW";
    }

    public int getIterationCount() {
        return this.f2822h;
    }

    public char[] getPassword() {
        return (char[]) this.f2820f.clone();
    }

    public byte[] getSalt() {
        return (byte[]) this.f2821g.clone();
    }

    public int hashCode() {
        int i2 = 1;
        int i3 = 0;
        while (true) {
            byte[] bArr = this.f2823i;
            if (i2 >= bArr.length) {
                return getAlgorithm().toLowerCase(Locale.ENGLISH).hashCode() ^ i3;
            }
            i3 += bArr[i2] * i2;
            i2++;
        }
    }
}
