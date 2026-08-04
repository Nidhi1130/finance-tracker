# Starter Accounts Design

## Goal

Add a practical starter set of accounts to the currently signed-in user's
Supabase data so the transaction form offers useful account choices.

## Accounts

- Cash
- Checking Account
- Savings Account
- Credit Card
- Debit Card
- PayPal
- Mobile Wallet
- Investment Account
- Loan Account
- Other

## Data behavior

Accounts remain private, user-owned records under the existing data model.
The seed operation uses the authenticated user's ID and skips names that
already exist for that user, ignoring letter case. The existing `cash` row is
therefore preserved instead of duplicated.

Existing transaction references are not modified. Every inserted account
remains editable and deletable through the Accounts page.

## Verification

After insertion, query Supabase for the user's account names and confirm that
all ten starter names exist exactly once when compared case-insensitively.
Then refresh the Accounts or Transactions page to load the updated list.
