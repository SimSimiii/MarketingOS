"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export function DeleteDocumentButton({ documentId }: { documentId: string }) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);

  async function handleClick() {
    setDeleting(true);
    try {
      await api.deleteKnowledgeDocument(documentId);
      toast.success("Document deleted");
      router.refresh();
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
