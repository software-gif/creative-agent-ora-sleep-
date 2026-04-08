"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import type { Creative } from "./CreativeCard";

type ApproveButtonProps = {
  creative: Creative;
};

export default function ApproveButton({ creative }: ApproveButtonProps) {
  const [updating, setUpdating] = useState(false);

  async function handleApprove() {
    if (updating || creative.approval_status === "approved") return;
    setUpdating(true);

    // Mark as approved (moves to Approved tab)
    await supabase
      .from("creatives")
      .update({ approval_status: "approved" })
      .eq("id", creative.id);

    setUpdating(false);
  }

  const isApproved = creative.approval_status === "approved";

  return (
    <button
      onClick={handleApprove}
      disabled={updating || isApproved}
      className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
        isApproved
          ? "bg-green-100 text-green-700"
          : "bg-green-500 text-white hover:bg-green-600"
      }`}
      title={isApproved ? "Approved" : "Approve"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-3.5 h-3.5"
      >
        <path
          fillRule="evenodd"
          d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
          clipRule="evenodd"
        />
      </svg>
      {isApproved ? "Approved" : "Approve"}
    </button>
  );
}
