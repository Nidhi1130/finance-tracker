import { requestJson } from "./api";

export interface Account {
  id: string;
  name: string;
  created_at: string;
}

interface AccountListResponse {
  items: Account[];
}

export async function listAccounts(): Promise<Account[]> {
  return (await requestJson<AccountListResponse>("/accounts")).items;
}
