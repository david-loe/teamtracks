import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import * as manifestApi from "@/api/manifest";
import * as organizationsApi from "@/api/organizations";
import type { SongManifest } from "@/types/manifest";
import PlayerView from "@/views/PlayerView.vue";

const engineMocks = vi.hoisted(() => {
  const behavior = {
    loadError: null as Error | null,
    holdLoad: true,
    initialProgressRatio: 0.5,
    startPromise: null as Promise<void> | null,
  };
  const instances: any[] = [];
  const pendingLoads: Array<() => void> = [];
  const ToneAudioEngine = vi.fn(function ToneAudioEngine() {
    let progressCallback: ((progress: { stemId: number; loadedBytes: number; totalBytes: number; ratio: number }) => void) | null = null;
    const engine = {
      initializeFromUserGesture: vi.fn(async () => {
        await behavior.startPromise;
      }),
      loadManifest: vi.fn(async (_manifest, onProgress) => {
        progressCallback = onProgress;
        engine.emitProgress(behavior.initialProgressRatio);
        if (behavior.loadError) {
          throw behavior.loadError;
        }
        if (behavior.holdLoad) {
          await new Promise<void>((resolve) => pendingLoads.push(resolve));
        }
      }),
      emitProgress: (ratio: number) => progressCallback?.({
        stemId: 1,
        loadedBytes: ratio * 100,
        totalBytes: 100,
        ratio,
      }),
      play: vi.fn(),
      pause: vi.fn(),
      stop: vi.fn(),
      seek: vi.fn(),
      setStemMuted: vi.fn(),
      setStemGain: vi.fn(),
      setFocus: vi.fn(),
      getCurrentTime: vi.fn(() => 0),
      getDuration: vi.fn(() => 120),
      dispose: vi.fn(),
    };
    instances.push(engine);
    return engine;
  });
  return { behavior, instances, pendingLoads, ToneAudioEngine };
});

const userSettingsMocks = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock("@/api/manifest", () => ({
  getSongManifest: vi.fn(),
}));

vi.mock("@/api/organizations", () => ({
  getBrowserSession: vi.fn(),
}));

vi.mock("@/audio/ToneAudioEngine", () => ({
  ToneAudioEngine: engineMocks.ToneAudioEngine,
}));

vi.mock("@/storage/userPlayerSettings", () => ({
  getUserPlayerSettings: userSettingsMocks.get,
}));

const manifest: SongManifest = {
  song: {
    id: 10,
    title: "Test Song",
    artist: "Test Artist",
    slug: "test-song",
    originalKey: 0,
    durationMs: 120000,
    sampleRate: 48000,
  },
  keyVariants: [{ id: 100, semitoneOffset: 0, isOriginal: true, status: "ready", playable: true, errorMessage: null }],
  selectedKeyId: 100,
  playable: true,
  stems: [
    {
      id: 1,
      name: "Drums",
      role: "drums",
      key: null,
      focusable: true,
      status: "ready",
      url: "/media/organizations/7/songs/10/keys/100/stems/1.m4a",
      codec: "aac",
      container: "m4a",
      channels: 2,
      sampleRate: 48000,
      durationMs: 120000,
      fileSizeBytes: 2048,
      bitrateKbps: 160,
      errorMessage: null,
    },
  ],
};

describe("PlayerView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    engineMocks.behavior.loadError = null;
    engineMocks.behavior.holdLoad = true;
    engineMocks.behavior.initialProgressRatio = 0.5;
    engineMocks.behavior.startPromise = null;
    engineMocks.instances.length = 0;
    engineMocks.pendingLoads.length = 0;
    userSettingsMocks.get.mockResolvedValue(null);
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: false,
      organizations: [],
    });
  });

  it("loads stems automatically and keeps controls disabled until loading completes", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const { wrapper } = await mountPlayerView();

    await flushPromises();

    expect(wrapper.text()).not.toContain("Audio aktivieren");
    expect(wrapper.text()).toContain("Stems laden");
    expect(wrapper.text()).toContain("50%");
    expect(engineMocks.ToneAudioEngine).toHaveBeenCalledTimes(1);
    expect(wrapper.find("#player-key").attributes("disabled")).toBeUndefined();
    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Stop").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".seek-control input").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".mute-button").attributes("disabled")).toBeDefined();
    expect(wrapper.find("#focus-stem").attributes("disabled")).toBeDefined();

    expect(engineMocks.ToneAudioEngine.mock.results[0].value.initializeFromUserGesture).not.toHaveBeenCalled();
  });

  it("shows decoding and hides load progress when controls become ready", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    engineMocks.behavior.initialProgressRatio = 1;

    const { wrapper } = await mountPlayerView();
    await vi.waitFor(() => expect(wrapper.text()).toContain("Stems werden dekodiert…"));

    expect(wrapper.find("#player-key").attributes("disabled")).toBeUndefined();
    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Stop").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".seek-control input").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".mute-button").attributes("disabled")).toBeDefined();
    expect(wrapper.find("#focus-stem").attributes("disabled")).toBeDefined();

    engineMocks.pendingLoads[0]?.();
    await vi.waitFor(() => expect(wrapper.find(".loading-progress").exists()).toBe(false));

    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeUndefined();
    expect(wrapper.find(".mute-button").attributes("disabled")).toBeUndefined();
    expect(wrapper.find("#focus-stem").attributes("disabled")).toBeUndefined();

    const pendingStart = deferred<void>();
    engineMocks.behavior.startPromise = pendingStart.promise;
    void buttonByText(wrapper, "Play").trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain("Audio wird gestartet..."));
    expect(wrapper.find("#player-key").attributes("disabled")).toBeUndefined();
    pendingStart.resolve();
    await flushPromises();
  });

  it("continues only the newly selected key when switching during decoding", async () => {
    engineMocks.behavior.initialProgressRatio = 1;
    vi.mocked(manifestApi.getSongManifest).mockImplementation(async (_organizationId, _songId, key) => manifestForKey(key ?? 0));

    const { wrapper } = await mountPlayerView();
    await vi.waitFor(() => expect(wrapper.text()).toContain("Stems werden dekodiert…"));

    await wrapper.find("#player-key").setValue("2");
    await vi.waitFor(() => expect(engineMocks.instances).toHaveLength(2));

    expect(engineMocks.instances[0].dispose).toHaveBeenCalledTimes(1);
    engineMocks.pendingLoads[0]?.();
    await flushPromises();

    expect(wrapper.find<HTMLSelectElement>("#player-key").element.value).toBe("2");
    expect(wrapper.text()).toContain("Stems werden dekodiert…");
    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeDefined();

    engineMocks.pendingLoads[1]?.();
    await vi.waitFor(() => expect(wrapper.find(".loading-progress").exists()).toBe(false));
    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeUndefined();
  });

  it("combines play and pause and exposes focus selection in the player overview", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const { wrapper } = await mountPlayerView();
    await flushPromises();

    expect(wrapper.find("#focus-stem").exists()).toBe(true);
    await wrapper.find("#focus-stem").setValue("1");
    expect(engineMocks.instances[0].setFocus).toHaveBeenLastCalledWith(expect.objectContaining({ stemId: 1 }));

    await buttonByText(wrapper, "Play").trigger("click");
    await flushPromises();
    expect(buttonByText(wrapper, "Pause").exists()).toBe(true);

    await buttonByText(wrapper, "Pause").trigger("click");
    expect(engineMocks.instances[0].pause).toHaveBeenCalledTimes(1);
    expect(buttonByText(wrapper, "Play").exists()).toBe(true);
  });

  it("offers a retry after a stem load error", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    engineMocks.behavior.loadError = new Error("Network error");

    const { wrapper } = await mountPlayerView();
    await flushPromises();

    expect(wrapper.text()).toContain("Network error");
    const retryButton = buttonByText(wrapper, "Stems erneut laden");

    engineMocks.behavior.loadError = null;
    await retryButton.trigger("click");
    await flushPromises();

    expect(engineMocks.ToneAudioEngine).toHaveBeenCalledTimes(2);
  });

  it("shows missing stems and disables key variants without playable assets", async () => {
    const partialManifest: SongManifest = {
      ...manifest,
      keyVariants: [
        { id: 100, semitoneOffset: 0, isOriginal: true, status: "draft", playable: true, errorMessage: null },
        { id: 101, semitoneOffset: 2, isOriginal: false, status: "draft", playable: false, errorMessage: null },
      ],
      stems: [
        ...manifest.stems,
        {
          ...manifest.stems[0],
          id: 2,
          name: "Bass",
          role: "bass",
          key: 0,
          status: "uploaded",
          url: null,
          codec: null,
          container: null,
        },
      ],
    };
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(partialManifest);

    const { wrapper } = await mountPlayerView();
    await flushPromises();

    expect(wrapper.text()).toContain("In dieser Tonart nicht verfügbare Stems:");
    expect(wrapper.find(".partial-stems-notice").text()).toContain("Bass");
    const options = wrapper.findAll("#player-key option");
    expect(options[0].attributes("disabled")).toBeUndefined();
    expect(options[1].attributes("disabled")).toBeDefined();
  });

  it("loads the requested musical key from the URL", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifestForKey(2));

    const { wrapper } = await mountPlayerView("/songs/10?key=2");
    await flushPromises();

    expect(manifestApi.getSongManifest).toHaveBeenCalledWith(7, 10, 2);
    expect(wrapper.find<HTMLSelectElement>("#player-key").element.value).toBe("2");
  });

  it("updates the URL and reloads the manifest when a key is selected", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockImplementation(async (_organizationId, _songId, key) => manifestForKey(key ?? 0));
    const { wrapper, router } = await mountPlayerView("/songs/10?view=mixer");
    await flushPromises();

    await wrapper.find("#player-key").setValue("2");
    await flushPromises();

    expect(router.currentRoute.value.query).toEqual({ view: "mixer", key: "2" });
    expect(manifestApi.getSongManifest).toHaveBeenLastCalledWith(7, 10, 2);
  });

  it("removes key when the original key is selected", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockImplementation(async (_organizationId, _songId, key) => manifestForKey(key ?? 0));
    const { wrapper, router } = await mountPlayerView("/songs/10?key=2&view=mixer");
    await flushPromises();

    await wrapper.find("#player-key").setValue("0");
    await flushPromises();

    expect(router.currentRoute.value.query).toEqual({ view: "mixer" });
    expect(manifestApi.getSongManifest).toHaveBeenLastCalledWith(7, 10, null);
  });

  it("reloads the selected key during browser back and forward navigation", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockImplementation(async (_organizationId, _songId, key) => manifestForKey(key ?? 0));
    const { wrapper, router } = await mountPlayerView();
    await flushPromises();

    await wrapper.find("#player-key").setValue("2");
    await flushPromises();
    await wrapper.find("#player-key").setValue("0");
    await flushPromises();

    router.back();
    await vi.waitFor(() => expect(router.currentRoute.value.query.key).toBe("2"));
    expect(manifestApi.getSongManifest).toHaveBeenLastCalledWith(7, 10, 2);

    router.forward();
    await vi.waitFor(() => expect(router.currentRoute.value.query.key).toBeUndefined());
    expect(manifestApi.getSongManifest).toHaveBeenLastCalledWith(7, 10, null);
  });

  it.each(["x", "12", "2&key=3"])("removes an invalid key query value: %s", async (keyQuery) => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifestForKey(0));

    const { router } = await mountPlayerView(`/songs/10?view=mixer&key=${keyQuery}`);
    await vi.waitFor(() => expect(router.currentRoute.value.query.key).toBeUndefined());

    expect(router.currentRoute.value.query.view).toBe("mixer");
    expect(manifestApi.getSongManifest).toHaveBeenLastCalledWith(7, 10, null);
  });

  it("canonicalizes an explicitly requested original key after loading the manifest", async () => {
    engineMocks.behavior.holdLoad = false;
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifestForKey(0));

    const { router } = await mountPlayerView("/songs/10?key=0&view=mixer");
    await vi.waitFor(() => expect(router.currentRoute.value.query.key).toBeUndefined());

    expect(manifestApi.getSongManifest).toHaveBeenNthCalledWith(1, 7, 10, 0);
    expect(router.currentRoute.value.query.view).toBe("mixer");
  });

  it("refreshes the session and redirects after organization access is revoked", async () => {
    vi.mocked(manifestApi.getSongManifest).mockRejectedValue(
      Object.assign(new Error("Organization login required"), { status: 401 }),
    );

    const { router } = await mountPlayerView();
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe("organizations"));

    expect(organizationsApi.getBrowserSession).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.query).toEqual({
      organizationId: "7",
      redirect: "/songs/10",
    });
  });
});

async function mountPlayerView(path = "/songs/10") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/songs/:id", component: { template: "<div />" } },
      { path: "/organizations", name: "organizations", component: { template: "<div />" } },
    ],
  });
  await router.push(path);
  await router.isReady();

  const wrapper = mount(PlayerView, {
    props: { organizationId: "7", id: "10" },
    global: {
      plugins: [createPinia(), router],
      stubs: {
        RouterLink: {
          template: "<a><slot /></a>",
        },
      },
    },
  });
  return { wrapper, router };
}

function manifestForKey(key: number): SongManifest {
  return {
    ...manifest,
    keyVariants: [
      { id: 100, semitoneOffset: 0, isOriginal: true, status: "ready", playable: true, errorMessage: null },
      { id: 101, semitoneOffset: 2, isOriginal: false, status: "ready", playable: true, errorMessage: null },
    ],
    selectedKeyId: key === 2 ? 101 : 100,
    stems: manifest.stems.map((stem) => ({
      ...stem,
      url: `/media/organizations/7/songs/10/keys/${key === 2 ? 101 : 100}/stems/${stem.id}.m4a`,
    })),
  };
}

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll("button").find((candidate) => candidate.text() === text);
  if (!button) {
    throw new Error(`Button not found: ${text}`);
  }
  return button;
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}
