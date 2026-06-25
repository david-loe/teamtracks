import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/api/organizations", () => ({
  getBrowserSession: vi.fn().mockResolvedValue({ authenticated: false, organizations: [] }),
  listOrganizations: vi.fn().mockResolvedValue([]),
}));

import App from "./App.vue";
import { router } from "./router";

describe("App", () => {
  it("renders the application shell", async () => {
    router.push("/organizations");
    await router.isReady();

    const wrapper = mount(App, {
      global: {
        plugins: [createPinia(), router],
      },
    });

    expect(wrapper.text()).toContain("TeamTracks");
    expect(wrapper.text()).toContain("Organisation auswählen");
  });
});
