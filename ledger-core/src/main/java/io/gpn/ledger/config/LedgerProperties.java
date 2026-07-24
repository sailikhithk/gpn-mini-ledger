package io.gpn.ledger.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * GPN ledger configuration. Bound from {@code gpn.ledger.*} properties.
 */
@Configuration
@ConfigurationProperties(prefix = "gpn.ledger")
@Getter
@Setter
public class LedgerProperties {

    private final Ledger ledger = new Ledger();
    private final Idempotency idempotency = new Idempotency();
    private final Audit audit = new Audit();

    @Getter
    @Setter
    public static class Ledger {
        /** Isolation level for all ledger writes (default SERIALIZABLE) */
        private String isolation = "SERIALIZABLE";
        /** Max retries on serialization failure (SQLSTATE 40001) */
        private int maxRetries = 3;
        /** Backoff base in milliseconds */
        private long retryBackoffMs = 50;
    }

    @Getter
    @Setter
    public static class Idempotency {
        /** Redis TTL for idempotency records in hours */
        private int ttlHours = 72;
        /** Fingerprint algorithm */
        private String fingerprintAlgorithm = "SHA-256";
    }

    @Getter
    @Setter
    public static class Audit {
        /** PostgreSQL advisory lock key for audit chain serialization */
        private long advisoryLockKey = 72718L;
        /** Genesis hash for the first entry in the chain */
        private String genesisHash = "GENESIS";
    }
}
