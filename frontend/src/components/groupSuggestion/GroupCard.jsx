import { useEffect, useState } from "react";
import GroupCard from "./GroupCard";
import MOCK_GROUPS from "./mockGroups";

const SHOW_MOCK_DATA = true;
const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("token");
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  let data = null;
  try {
    data = await response.json();
  } catch {}
  if (!response.ok) {
    const message =
      (data && (data.message || data.detail)) || "خطا در ارتباط با سرور";
    throw new Error(message);
  }
  return data;
}
function GroupList({ filters, onJoinGroup, onGroupsLoaded }) {
  const [groups, setGroups] = useState(SHOW_MOCK_DATA ? MOCK_GROUPS : []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!filters) return;

    async function loadGroups() {
      try {
        setLoading(true);
        setError("");

        const response = await apiRequest("/groups/recommend", {
          method: "POST",
          body: JSON.stringify(filters),
        });

        const result = response?.data?.groups || [];
        setGroups(
          result.length > 0 ? result : SHOW_MOCK_DATA ? MOCK_GROUPS : [],
        );
        if (onGroupsLoaded) onGroupsLoaded(result.length);
      } catch (err) {
        setGroups(SHOW_MOCK_DATA ? MOCK_GROUPS : []);
        setError(err.message || "خطا در دریافت گروه‌ها");
      } finally {
        setLoading(false);
      }
    }

    loadGroups();
  }, [filters]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-[#185E64]">در حال جستجوی گروه مناسب...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-700 bg-red-50 border border-red-200 p-4 rounded-xl text-sm">
        {error}
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="text-center py-10">
        <p className="text-[#185E64] text-opacity-70">
          گروه مناسبی با این فیلترها پیدا نشد. فیلترها را تغییر دهید و دوباره
          تلاش کنید.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {groups.map((group) => (
        <GroupCard key={group.id} group={group} onJoinGroup={onJoinGroup} />
      ))}
    </div>
  );
}

export default GroupList;
