package io.gpn.ledger.domain;

/**
 * Account types following standard accounting conventions.
 * The type determines the normal balance side (debit or credit).
 */
public enum AccountType {
    /** Assets: debit normal balance (cash, receivables) */
    ASSET,
    /** Liabilities: credit normal balance (payables, customer funds) */
    LIABILITY,
    /** Revenue: credit normal balance (fees, interest) */
    REVENUE,
    /** Expenses: debit normal balance (costs, losses) */
    EXPENSE
}
