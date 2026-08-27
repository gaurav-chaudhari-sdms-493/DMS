export interface OfflineAction {
  id: string;
  type: "create_folder" | "rename_folder" | "delete_folder" | "delete_document" | "rename_document";
  payload: any;
  timestamp: number;
}

export interface PendingUpload {
  id: string;
  name: string;
  size: number;
  type: string;
  folderId?: string | null;
  base64Data: string;
  timestamp: number;
}

const STORAGE_KEYS = {
  DRIVE_STATS: "dms_offline_drive_stats",
  FOLDER_TREE: "dms_offline_folder_tree",
  DOCUMENTS_PREFIX: "dms_offline_docs_",
  DOC_DETAIL_PREFIX: "dms_offline_detail_",
  OFFLINE_ACTIONS: "dms_offline_actions",
  PENDING_UPLOADS: "dms_offline_pending_uploads",
};

// Safe localStorage access
const getItem = <T>(key: string, fallback: T): T => {
  if (typeof window === "undefined") return fallback;
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : fallback;
  } catch (e) {
    console.error(`Error reading ${key} from localStorage`, e);
    return fallback;
  }
};

const setItem = (key: string, value: any): void => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error(`Error saving ${key} to localStorage`, e);
  }
};

// Data Caching API
export const offlineStore = {
  // Drive Stats
  saveStats: (stats: any) => setItem(STORAGE_KEYS.DRIVE_STATS, stats),
  getStats: () => getItem<any>(STORAGE_KEYS.DRIVE_STATS, null),

  // Folder Tree
  saveFolderTree: (tree: any) => setItem(STORAGE_KEYS.FOLDER_TREE, tree),
  getFolderTree: () => getItem<any[]>(STORAGE_KEYS.FOLDER_TREE, []),

  // Documents by Folder
  saveDocuments: (folderId: string | null | undefined, docs: any[]) => {
    const key = `${STORAGE_KEYS.DOCUMENTS_PREFIX}${folderId || "root"}`;
    setItem(key, docs);
  },
  getDocuments: (folderId: string | null | undefined): any[] => {
    const key = `${STORAGE_KEYS.DOCUMENTS_PREFIX}${folderId || "root"}`;
    return getItem<any[]>(key, []);
  },

  // Document Detail
  saveDocumentDetail: (docId: string, detail: any) => {
    setItem(`${STORAGE_KEYS.DOC_DETAIL_PREFIX}${docId}`, detail);
  },
  getDocumentDetail: (docId: string): any => {
    return getItem<any>(`${STORAGE_KEYS.DOC_DETAIL_PREFIX}${docId}`, null);
  },

  // Offline CRUD Queue
  getActions: (): OfflineAction[] => getItem<OfflineAction[]>(STORAGE_KEYS.OFFLINE_ACTIONS, []),
  
  addAction: (action: Omit<OfflineAction, "id" | "timestamp">) => {
    const actions = offlineStore.getActions();
    const newAction: OfflineAction = {
      ...action,
      id: `act_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      timestamp: Date.now(),
    };
    actions.push(newAction);
    setItem(STORAGE_KEYS.OFFLINE_ACTIONS, actions);
    return newAction;
  },

  removeAction: (id: string) => {
    const actions = offlineStore.getActions().filter((a) => a.id !== id);
    setItem(STORAGE_KEYS.OFFLINE_ACTIONS, actions);
  },

  clearActions: () => setItem(STORAGE_KEYS.OFFLINE_ACTIONS, []),

  // Pending File Upload Queue
  getPendingUploads: (): PendingUpload[] => getItem<PendingUpload[]>(STORAGE_KEYS.PENDING_UPLOADS, []),

  addPendingUpload: async (file: File, folderId?: string | null): Promise<PendingUpload> => {
    const base64Data = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    const uploads = offlineStore.getPendingUploads();
    const newUpload: PendingUpload = {
      id: `up_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      folderId: folderId || null,
      base64Data,
      timestamp: Date.now(),
    };

    uploads.push(newUpload);
    setItem(STORAGE_KEYS.PENDING_UPLOADS, uploads);

    // Also add to local cached document list so it appears in UI immediately!
    const folderKey = folderId || "root";
    const cachedDocs = offlineStore.getDocuments(folderId);
    const mockDoc = {
      id: newUpload.id,
      title: file.name,
      file_type: file.name.split(".").pop() || "file",
      size_bytes: file.size,
      status: "pending_upload",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      folder_id: folderId || null,
      is_offline_pending: true,
    };
    offlineStore.saveDocuments(folderId, [mockDoc, ...cachedDocs]);

    return newUpload;
  },

  removePendingUpload: (id: string) => {
    const uploads = offlineStore.getPendingUploads().filter((u) => u.id !== id);
    setItem(STORAGE_KEYS.PENDING_UPLOADS, uploads);
  },

  clearPendingUploads: () => setItem(STORAGE_KEYS.PENDING_UPLOADS, []),

  // Helper to check pending count
  getPendingCount: (): number => {
    return offlineStore.getActions().length + offlineStore.getPendingUploads().length;
  },
};

// Convert Base64 back to File object
function base64ToFile(base64Data: string, fileName: string, fileType: string): File {
  const arr = base64Data.split(",");
  const mime = arr[0].match(/:(.*?);/)?.[1] || fileType;
  const bstr = atob(arr[1] || arr[0]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], fileName, { type: mime });
}

// Auto-sync function when internet connectivity returns
export async function syncOfflineData(api: any): Promise<{ syncedActions: number; uploadedFiles: number; errors: string[] }> {
  let syncedActions = 0;
  let uploadedFiles = 0;
  const errors: string[] = [];

  const actions = offlineStore.getActions();
  const uploads = offlineStore.getPendingUploads();

  // 1. Replay CRUD actions sequentially
  for (const action of actions) {
    try {
      if (action.type === "create_folder") {
        await api.folders.create(action.payload.name, action.payload.parent_id);
      } else if (action.type === "rename_folder") {
        await api.folders.update(action.payload.folder_id, action.payload.new_name);
      } else if (action.type === "delete_folder") {
        if (api.folders.deletePermanent) {
          await api.folders.deletePermanent(action.payload.folder_id).catch(() => {});
        } else if (api.folders.moveToTrash) {
          await api.folders.moveToTrash(action.payload.folder_id).catch(() => {});
        }
      } else if (action.type === "delete_document") {
        if (api.documents.deletePermanent) {
          await api.documents.deletePermanent(action.payload.doc_id).catch(() => {});
        } else if (api.documents.moveToTrash) {
          await api.documents.moveToTrash(action.payload.doc_id).catch(() => {});
        }
      }
      offlineStore.removeAction(action.id);
      syncedActions++;
    } catch (e: any) {
      console.error(`Failed to sync offline action ${action.id}:`, e);
      errors.push(`Action ${action.type}: ${e.message || "Failed"}`);
      // Remove failed action to prevent endless retry deadlock
      offlineStore.removeAction(action.id);
    }
  }

  // 2. Upload pending files
  for (const upload of uploads) {
    try {
      const fileObj = base64ToFile(upload.base64Data, upload.name, upload.type);
      await api.documents.upload(fileObj, upload.folderId);
      offlineStore.removePendingUpload(upload.id);
      uploadedFiles++;
    } catch (e: any) {
      console.error(`Failed to upload pending file ${upload.name}:`, e);
      errors.push(`Upload ${upload.name}: ${e.message || "Failed"}`);
    }
  }

  return { syncedActions, uploadedFiles, errors };
}
