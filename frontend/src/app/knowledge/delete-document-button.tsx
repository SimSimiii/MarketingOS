"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { refreshPage } from "@/lib/page-data";

export function DeleteDocumentButton({ documentId }: { documentId: string }) {
  const [deleting, setDeleting] = useState(false);

  async function handleClick() {
    setDeleting(true);
    try {
      await api.deleteKnowledgeDocument(documentId);
      toast.success("Document deleted");
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to delete document");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleClick} disabled={deleting}>
      {deleting ? "Deleting..." : "Delete"}
    </Button>
  );
}
