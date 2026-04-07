"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";

type Folder = {
  id: string;
  name: string;
  parent_folder_id: string | null;
  sort_order: number;
};

type FolderSidebarProps = {
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onDrop?: (folderId: string, creativeId: string) => void;
};

export default function FolderSidebar({
  selectedFolderId,
  onSelectFolder,
  onDrop,
}: FolderSidebarProps) {
  const { brandId } = useBrand();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [dragOver, setDragOver] = useState<string | null>(null);

  useEffect(() => {
    if (brandId) loadFolders();
  }, [brandId]);

  async function loadFolders() {
    const { data } = await supabase
      .from("asset_folders")
      .select("*")
      .eq("brand_id", brandId!)
      .order("sort_order")
      .order("name");

    if (data) setFolders(data);
  }

  async function createFolder() {
    if (!newName.trim() || !brandId) return;
    const { error } = await supabase.from("asset_folders").insert({
      brand_id: brandId,
      name: newName.trim(),
    });
    if (error) return;
    setNewName("");
    setCreating(false);
    loadFolders();
  }

  async function deleteFolder(folderId: string) {
    const { error } = await supabase.from("asset_folders").delete().eq("id", folderId);
    if (error) return;
    if (selectedFolderId === folderId) onSelectFolder(null);
    loadFolders();
  }

  function handleDragOver(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    setDragOver(folderId);
  }

  function handleDragLeave() {
    setDragOver(null);
  }

  function handleDrop(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    setDragOver(null);
    const creativeId = e.dataTransfer.getData("creative-id");
    if (creativeId && onDrop) {
      onDrop(folderId, creativeId);
    }
  }

  return (
    <div className="w-56 border-r border-gray-200 bg-white p-4 flex flex-col gap-1">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Ordner
      </h2>

      {/* All Assets */}
      <button
        onClick={() => onSelectFolder(null)}
        className={`text-left text-sm px-3 py-2 rounded-lg transition-colors ${
          selectedFolderId === null
            ? "bg-gray-100 text-gray-900 font-medium"
            : "text-gray-600 hover:bg-gray-50"
        }`}
      >
        Alle Assets
      </button>

      {/* Folders */}
      {folders.map((folder) => (
        <div
          key={folder.id}
          className={`group flex items-center rounded-lg transition-colors ${
            dragOver === folder.id ? "bg-amber-50 ring-2 ring-amber-300" : ""
          } ${
            selectedFolderId === folder.id
              ? "bg-gray-100"
              : "hover:bg-gray-50"
          }`}
          onDragOver={(e) => handleDragOver(e, folder.id)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, folder.id)}
        >
          <button
            onClick={() => onSelectFolder(folder.id)}
            className={`flex-1 text-left text-sm px-3 py-2 ${
              selectedFolderId === folder.id
                ? "text-gray-900 font-medium"
                : "text-gray-600"
            }`}
          >
            {folder.name}
          </button>
          <button
            onClick={() => deleteFolder(folder.id)}
            className="hidden group-hover:block text-gray-300 hover:text-red-400 pr-2 text-xs"
            title="Ordner löschen"
          >
            ×
          </button>
        </div>
      ))}

      {/* Create folder */}
      {creating ? (
        <div className="mt-2 flex gap-1">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createFolder()}
            placeholder="Ordnername"
            className="flex-1 text-sm border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:border-gray-400"
            autoFocus
          />
          <button
            onClick={createFolder}
            className="text-xs text-gray-500 hover:text-gray-700 px-1"
          >
            OK
          </button>
        </div>
      ) : (
        <button
          onClick={() => setCreating(true)}
          className="mt-2 text-left text-sm text-gray-400 hover:text-gray-600 px-3 py-2"
        >
          + Neuer Ordner
        </button>
      )}
    </div>
  );
}
