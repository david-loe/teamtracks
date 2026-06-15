import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { Stem, StemUploadInput } from "@/api/stems";
import StemUpload from "@/components/StemUpload.vue";

describe("StemUpload", () => {
  it("creates editable rows with filename names and the song original key", async () => {
    const wrapper = mount(StemUpload, {
      props: { originalKey: 9, upload: vi.fn().mockResolvedValue([]) },
    });

    await selectFiles(wrapper, [wavFile("drums.wav"), wavFile("lead.vocals.wav")]);

    expect(wrapper.findAll(".upload-row")).toHaveLength(2);
    expect(inputValue(wrapper, "#stem-upload-name-1")).toBe("drums");
    expect(inputValue(wrapper, "#stem-upload-name-2")).toBe("lead.vocals");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("A");
    expect(selectedText(wrapper, "#stem-upload-key-2")).toBe("A");

    await wrapper.find("#stem-upload-role-1").setValue("drums");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("tonartunabhaengig");
    expect(wrapper.find("#stem-upload-key-1").attributes("disabled")).toBeUndefined();

    await wrapper.find("#stem-upload-key-1").setValue("4");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("E");

    await wrapper.find("#stem-upload-role-1").setValue("vocals");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("E");

    await wrapper.find("#stem-upload-role-1").setValue("click_cue");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("tonartunabhaengig");

    await wrapper.find("#stem-upload-role-1").setValue("vocals");
    expect(selectedText(wrapper, "#stem-upload-key-1")).toBe("A");

    await wrapper.findAll("button").find((button) => button.text() === "Entfernen")!.trigger("click");
    expect(wrapper.findAll(".upload-row")).toHaveLength(1);
  });

  it("removes successful uploads and retains failed rows for retry", async () => {
    const upload = vi.fn(async (inputs: StemUploadInput[]) => [
      { input: inputs[0], stem: stemFor(inputs[0], 1), error: null },
      { input: inputs[1], stem: null, error: "Datei zu gross" },
    ]);
    const wrapper = mount(StemUpload, {
      props: { originalKey: 2, upload },
    });

    await selectFiles(wrapper, [wavFile("bass.wav"), wavFile("vocals.wav")]);
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(upload).toHaveBeenCalledTimes(1);
    expect(upload.mock.calls[0][0].map((input) => [input.name, input.role, input.key])).toEqual([
      ["bass", "other", 2],
      ["vocals", "other", 2],
    ]);
    expect(wrapper.findAll(".upload-row")).toHaveLength(1);
    expect(inputValue(wrapper, "#stem-upload-name-2")).toBe("vocals");
    expect(wrapper.text()).toContain("Datei zu gross");
  });
});

function wavFile(name: string): File {
  return new File(["wav"], name, { type: "audio/wav" });
}

async function selectFiles(wrapper: ReturnType<typeof mount>, files: File[]): Promise<void> {
  const input = wrapper.find("#stem-upload-files");
  Object.defineProperty(input.element, "files", { configurable: true, value: files });
  await input.trigger("change");
}

function inputValue(wrapper: ReturnType<typeof mount>, selector: string): string {
  return (wrapper.find(selector).element as HTMLInputElement).value;
}

function selectedText(wrapper: ReturnType<typeof mount>, selector: string): string {
  return (wrapper.find(selector).element as HTMLSelectElement).selectedOptions[0]?.textContent ?? "";
}

function stemFor(input: StemUploadInput, id: number): Stem {
  return {
    id,
    songId: 10,
    name: input.name,
    role: input.role,
    key: input.key ?? null,
    status: "uploaded",
    sourceFilename: input.file.name,
    sourceFormat: "wav",
    codec: null,
    sampleRate: null,
    channels: null,
    durationMs: null,
    fileSizeBytes: input.file.size,
    bitrateKbps: null,
    errorMessage: null,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  };
}
