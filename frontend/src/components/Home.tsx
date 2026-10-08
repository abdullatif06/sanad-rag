"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type DocumentInfo } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useLanguage } from "@/lib/i18n";
import { clearWorkspaceKey, loadWorkspaceKey, saveWorkspaceKey } from "@/lib/workspace";
import { Intro } from "./Intro";
import { Workspace } from "./Workspace";

const SAMPLE_URL = "/samples/noqta-cafe-policies.md";
const SAMPLE_NAME = "noqta-cafe-policies.md";

export function Home() {
  const { t } = useLanguage();
  const [publicKey, setPublicKey] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Resume a saved demo workspace, if it still exists on the server.
  useEffect(() => {
    const saved = loadWorkspaceKey();
    if (!saved) return;
    api
      .listDocuments(saved)
      .then((docs) => {
        setPublicKey(saved);
        setDocuments(docs);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) clearWorkspaceKey();
      });
  }, []);

  const upload = useCallback(
    async (file: File) => {
      setError(null);
      try {
        let key = publicKey;
        if (!key) {
          setBusy(t.creatingWorkspace);
          key = (await api.createDemo()).public_key;
          saveWorkspaceKey(key);
          setPublicKey(key);
        }
        setBusy(t.uploading(file.name));
        const document = await api.upload(key, file);
        setDocuments((docs) => [...docs, document]);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          clearWorkspaceKey();
          setPublicKey(null);
        }
        setError(errorMessage(e, t));
      } finally {
        setBusy(null);
      }
    },
    [publicKey, t],
  );

  const uploadSample = useCallback(async () => {
    const blob = await fetch(SAMPLE_URL).then((r) => r.blob());
    await upload(new File([blob], SAMPLE_NAME, { type: "text/markdown" }));
  }, [upload]);

  const startOver = useCallback(() => {
    clearWorkspaceKey();
    setPublicKey(null);
    setDocuments([]);
    setError(null);
  }, []);

  if (publicKey && documents.length > 0) {
    return (
      <Workspace
        publicKey={publicKey}
        documents={documents}
        busy={busy}
        error={error}
        onFile={upload}
        onStartOver={startOver}
      />
    );
  }
  return <Intro busy={busy} error={error} onFile={upload} onSample={uploadSample} />;
}
