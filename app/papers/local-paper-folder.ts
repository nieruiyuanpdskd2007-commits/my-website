"use client";

export type PaperDirectoryHandle = FileSystemDirectoryHandle & {
  queryPermission?: (options: { mode: "readwrite" }) => Promise<PermissionState>;
  requestPermission?: (options: { mode: "readwrite" }) => Promise<PermissionState>;
};

type DirectoryPickerWindow = Window & {
  showDirectoryPicker?: (options?: {
    id?: string;
    mode?: "read" | "readwrite";
    startIn?: "desktop" | "documents" | "downloads";
  }) => Promise<PaperDirectoryHandle>;
};

const databaseName = "ruiyuan-paper-library";
const storeName = "settings";
const directoryKey = "paper-download-directory";

export function supportsPaperDirectoryPicker() {
  return typeof window !== "undefined" && "showDirectoryPicker" in window;
}

function openDatabase() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(databaseName, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(storeName)) {
        request.result.createObjectStore(storeName);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function loadPaperDirectory() {
  if (!supportsPaperDirectoryPicker()) return null;
  const database = await openDatabase();
  return new Promise<PaperDirectoryHandle | null>((resolve, reject) => {
    const transaction = database.transaction(storeName, "readonly");
    const request = transaction.objectStore(storeName).get(directoryKey);
    request.onsuccess = () => resolve((request.result as PaperDirectoryHandle | undefined) ?? null);
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

async function rememberPaperDirectory(handle: PaperDirectoryHandle) {
  const database = await openDatabase();
  return new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(storeName, "readwrite");
    transaction.objectStore(storeName).put(handle, directoryKey);
    transaction.oncomplete = () => {
      database.close();
      resolve();
    };
    transaction.onerror = () => reject(transaction.error);
  });
}

export async function choosePaperDirectory() {
  const picker = (window as DirectoryPickerWindow).showDirectoryPicker;
  if (!picker) throw new Error("此浏览器不支持文件夹授权。");
  const handle = await picker.call(window, {
    id: "ruiyuan-paper-library",
    mode: "readwrite",
    startIn: "desktop",
  });
  await rememberPaperDirectory(handle);
  return handle;
}

export async function canWritePaperDirectory(handle: PaperDirectoryHandle, request = false) {
  const options = { mode: "readwrite" as const };
  if (!handle.queryPermission || !handle.requestPermission) return true;
  if (await handle.queryPermission(options) === "granted") return true;
  return request && await handle.requestPermission(options) === "granted";
}

function safePdfFilename(title: string) {
  const cleaned = title.replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, " ").trim();
  return `${cleaned.slice(0, 160) || "paper"}.pdf`;
}

export async function savePaperPdf(handle: PaperDirectoryHandle, slug: string, title: string) {
  const response = await fetch(`/papers/download/${encodeURIComponent(slug)}`, {
    credentials: "same-origin",
  });
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.toLowerCase().includes("pdf")) {
    throw new Error("PDF 暂时无法下载。");
  }

  const fileHandle = await handle.getFileHandle(safePdfFilename(title), { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(await response.blob());
  await writable.close();
}
