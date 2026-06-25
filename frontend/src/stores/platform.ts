import { defineStore } from "pinia";
import { ref } from "vue";

import { ApiError } from "@/api/client";
import * as platformApi from "@/api/platform";

export const usePlatformStore = defineStore("platform", () => {
  const authenticated = ref(false);
  const initialized = ref(false);

  async function initialize(): Promise<void> {
    if (initialized.value) return;
    try {
      authenticated.value = (await platformApi.getPlatformSession()).authenticated;
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      authenticated.value = false;
    } finally {
      initialized.value = true;
    }
  }

  async function login(password: string): Promise<void> {
    authenticated.value = (await platformApi.loginPlatform(password)).authenticated;
    initialized.value = true;
  }

  async function logout(): Promise<void> {
    await platformApi.logoutPlatform();
    authenticated.value = false;
    initialized.value = true;
  }

  return { authenticated, initialized, initialize, login, logout };
});
