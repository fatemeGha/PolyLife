import { useState } from "react";
import {
  workoutTypeLabels,
  difficultyLabels,
  riskLabels,
  goalLabels,
  dayLabels,
} from "./constants/labels";

function GroupCard({ group, onJoinGroup }) {
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState("");

  const formatTime = (timeString) => {
    if (!timeString) return "";
    const [hours, minutes] = timeString.split(":");
    return `${hours}:${minutes}`;
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case "low":
        return "text-green-600 bg-green-50";
      case "medium":
        return "text-yellow-600 bg-yellow-50";
      case "high":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  const handleJoinGroup = async () => {
    setIsJoining(true);
    setJoinError("");
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/api/memberships", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          group_id: group.id,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        alert("✅ عضویت شما با موفقیت ثبت شد!");
        if (onJoinGroup) onJoinGroup(group.id);
      } else {
        setJoinError(data.message || "خطا در ثبت عضویت");
      }
    } catch (err) {
      setJoinError("خطا در ارتباط با سرور");
    } finally {
      setIsJoining(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border-2 border-[#BCDADD] hover:shadow-xl transition-shadow duration-300">
      <h3 className="text-xl font-bold text-[#185E64] mb-3 flex items-center gap-2">
        <span>🏛️</span>
        {group.name}
      </h3>

      <div className="space-y-2.5">
        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">🎯 هدف:</span>
          <span className="bg-[#CDF1F4] px-3 py-1 rounded-full text-xs">
            {goalLabels[group.goal?.name] || group.goal?.name || "نامشخص"}
          </span>
        </p>

        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">🏋️ نوع تمرین:</span>
          <span className="bg-[#CDF1F4] px-3 py-1 rounded-full text-xs">
            {workoutTypeLabels[group.workout_type] || group.workout_type}
          </span>
        </p>

        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">📊 سطح سختی:</span>
          <span className="bg-[#CDF1F4] px-3 py-1 rounded-full text-xs">
            {difficultyLabels[group.difficulty_level] || group.difficulty_level}
          </span>
        </p>

        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">🕐 زمان:</span>
          <span className="bg-[#CDF1F4] px-3 py-1 rounded-full text-xs">
            {formatTime(group.start_time)} تا {formatTime(group.end_time)}
          </span>
        </p>

        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">📅 روزها:</span>
          <span className="flex flex-wrap gap-1">
            {group.days?.map((day, index) => (
              <span key={index} className="bg-[#CDF1F4] px-2 py-0.5 rounded-full text-xs">
                {dayLabels[day] || day}
              </span>
            ))}
          </span>
        </p>

        <p className="text-sm text-[#185E64] flex items-center gap-2">
          <span className="font-medium min-w-[90px]">👥 اعضا:</span>
          <span className="bg-[#CDF1F4] px-3 py-1 rounded-full text-xs">
            {group.member_count || 0} از {group.max_members || 0}
          </span>
        </p>

        {group.match_score !== undefined && (
          <p className="text-sm text-[#185E64] flex items-center gap-2">
            <span className="font-medium min-w-[90px]">⭐ امتیاز تطبیق:</span>
            <span className="bg-[#FDE6C3] px-3 py-1 rounded-full text-xs font-bold">
              {group.match_score}%
            </span>
          </p>
        )}

        {group.risk && (
          <p className="text-sm flex items-center gap-2">
            <span className="font-medium min-w-[90px] text-[#185E64]">⚠️ سطح ریسک:</span>
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${getRiskColor(group.risk.level)}`}>
              {riskLabels[group.risk.level] || group.risk.level}
            </span>
          </p>
        )}

        {joinError && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-1 rounded-lg flex items-center gap-1">
            <span>❌</span> {joinError}
          </p>
        )}
      </div>

      <div className="mt-5 flex gap-3">
        <button
          onClick={handleJoinGroup}
          disabled={isJoining}
          className="flex-1 bg-[#FDE6C3] hover:bg-[#f5d4a8] text-[#185E64] font-bold py-2.5 px-4 rounded-xl transition-all duration-200 border-2 border-[#185E64] border-opacity-20 shadow-md hover:shadow-lg text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isJoining ? (
            <>
              <span>⏳</span> در حال ثبت...
            </>
          ) : (
            <>
              <span>➕</span> عضویت در گروه
            </>
          )}
        </button>

        <button
          onClick={() => window.location.href = `/groups/${group.id}`}
          className="flex-1 bg-white hover:bg-[#CDF1F4] text-[#185E64] font-semibold py-2.5 px-4 rounded-xl transition-all duration-200 border-2 border-[#BCDADD] text-sm flex items-center justify-center gap-2"
        >
          <span>👁️</span> مشاهده جزئیات
        </button>
      </div>
    </div>
  );
}

export default GroupCard;