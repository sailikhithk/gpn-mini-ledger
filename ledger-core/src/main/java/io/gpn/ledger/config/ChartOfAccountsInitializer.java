package io.gpn.ledger.config;

import io.gpn.ledger.domain.Account;
import io.gpn.ledger.domain.AccountType;
import io.gpn.ledger.repository.AccountRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Seeds the chart of accounts on startup if they do not exist.
 *
 * <p>The four accounts model a minimal payment system:
 * <ul>
 *   <li>{@code merchant_receivable} (ASSET) - what the merchant is owed</li>
 *   <li>{@code customer_liability} (LIABILITY) - customer funds on hold</li>
 *   <li>{@code merchant_revenue} (REVENUE) - captured revenue</li>
 *   <li>{@code settlement_clearing} (ASSET) - funds in transit to network</li>
 * </ul>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChartOfAccountsInitializer {

    private final AccountRepository accountRepository;

    @EventListener(ApplicationReadyEvent.class)
    @Transactional
    public void seedAccounts() {
        createIfAbsent("merchant_receivable", AccountType.ASSET,     "USD");
        createIfAbsent("customer_liability",  AccountType.LIABILITY, "USD");
        createIfAbsent("merchant_revenue",    AccountType.REVENUE,   "USD");
        createIfAbsent("settlement_clearing", AccountType.ASSET,     "USD");
        log.info("Chart of accounts seeded (4 accounts)");
    }

    private void createIfAbsent(String code, AccountType type, String currency) {
        if (accountRepository.findByCode(code).isEmpty()) {
            accountRepository.save(Account.builder()
                .code(code)
                .type(type)
                .currency(currency)
                .build());
        }
    }
}
