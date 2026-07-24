import { useState, useEffect } from "react";

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

const DEFAULT_FITNESS_LEVELS = [
  { value: "beginner", label: "مبتدی" },
  { value: "intermediate", label: "متوسط" },
  { value: "advanced", label: "پیشرفته" },
];

const DEFAULT_WORKOUT_TYPES = [
  { value: "gym", label: "بدنسازی" },
  { value: "running", label: "دویدن" },
  { value: "swimming", label: "شنا" },
  { value: "yoga", label: "یوگا" },
];

const DEFAULT_GOALS = [
  { id: "weight_loss", name: "کاهش وزن" },
  { id: "muscle_gain", name: "عضله‌سازی" },
  { id: "general_fitness", name: "تناسب اندام عمومی" },
];

const DEFAULT_EQUIPMENT = [
  { id: "dumbbell", name: "دمبل" },
  { id: "mat", name: "مت ورزشی" },
  { id: "resistance_band", name: "کش مقاومتی" },
];

const DEFAULT_INJURY_OPTIONS = [
  { id: "knee", name: "زانو" },
  { id: "back", name: "کمر" },
  { id: "shoulder", name: "شانه" },
];

const days = [
  "Saturday",
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
];

const dayLabelsFa = {
  Saturday: "شنبه",
  Sunday: "یکشنبه",
  Monday: "دوشنبه",
  Tuesday: "سه‌شنبه",
  Wednesday: "چهارشنبه",
  Thursday: "پنج‌شنبه",
  Friday: "جمعه",
};

function FilterPanel({ onSearch }) {
  const [formData, setFormData] = useState({
    goalId: "",
    fitnessLevel: "",
    workoutType: "",
    availableDays: [],
    preferredStartTime: "",
    preferredEndTime: "",
  });

  const [options, setOptions] = useState({
    fitnessLevels: DEFAULT_FITNESS_LEVELS,
    workoutTypes: DEFAULT_WORKOUT_TYPES,
  });

  const [goals, setGoals] = useState(DEFAULT_GOALS);
  const [equipment, setEquipment] = useState(DEFAULT_EQUIPMENT);
  const [injuryOptions, setInjuryOptions] = useState(DEFAULT_INJURY_OPTIONS);
  const [userInjuries, setUserInjuries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEquipment, setSelectedEquipment] = useState([]);
  const [selectedInjuries, setSelectedInjuries] = useState([]);
  const [hasInjuryHistory, setHasInjuryHistory] = useState(false);

  useEffect(() => {
    const fetchOptions = async () => {
      const [optionsRes, goalsRes, equipmentRes, injuryRes, profileRes] =
        await Promise.allSettled([
          apiRequest("/options"),
          apiRequest("/goals"),
          apiRequest("/equipment"),
          apiRequest("/injury-options"),
          apiRequest("/profile"),
        ]);

      if (optionsRes.status === "fulfilled" && optionsRes.value?.success) {
        setOptions({
          fitnessLevels:
            optionsRes.value.data.fitness_levels || DEFAULT_FITNESS_LEVELS,
          workoutTypes:
            optionsRes.value.data.workout_types || DEFAULT_WORKOUT_TYPES,
        });
      }

      if (goalsRes.status === "fulfilled" && goalsRes.value?.success) {
        setGoals(goalsRes.value.data.goals || DEFAULT_GOALS);
      }

      if (equipmentRes.status === "fulfilled" && equipmentRes.value?.success) {
        setEquipment(equipmentRes.value.data.equipment || DEFAULT_EQUIPMENT);
      }

      if (injuryRes.status === "fulfilled" && injuryRes.value?.success) {
        setInjuryOptions(
          injuryRes.value.data.injuries || DEFAULT_INJURY_OPTIONS,
        );
      }

      if (profileRes.status === "fulfilled" && profileRes.value?.success) {
        const injuriesList = profileRes.value.data.profile.injury_history || [];
        setUserInjuries(injuriesList);
        if (injuriesList.length > 0) {
          setHasInjuryHistory(true);
          setSelectedInjuries(
            injuriesList.map((injury) => injury.id || injury),
          );
        }
      }

      // فقط اگه همه‌ی درخواست‌ها شکست بخورن پیام خطا نشون بده
      const allFailed = [
        optionsRes,
        goalsRes,
        equipmentRes,
        injuryRes,
        profileRes,
      ].every((r) => r.status === "rejected");
      if (allFailed) {
        setError(
          "در دریافت اطلاعات از سرور مشکلی پیش آمد. مقادیر پیش‌فرض نمایش داده می‌شود.",
        );
      }

      setLoading(false);
    };

    fetchOptions();
  }, []);

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const toggleDay = (day) => {
    setFormData((prev) => ({
      ...prev,
      availableDays: prev.availableDays.includes(day)
        ? prev.availableDays.filter((d) => d !== day)
        : [...prev.availableDays, day],
    }));
  };

  const toggleEquipment = (equipId) => {
    setSelectedEquipment((prev) =>
      prev.includes(equipId)
        ? prev.filter((id) => id !== equipId)
        : [...prev, equipId],
    );
  };

  const toggleInjury = (injuryId) => {
    setSelectedInjuries((prev) =>
      prev.includes(injuryId)
        ? prev.filter((id) => id !== injuryId)
        : [...prev, injuryId],
    );
  };

  const handleSubmit = () => {
    if (!formData.goalId || !formData.fitnessLevel || !formData.workoutType) {
      setError("لطفاً تمام فیلدهای ضروری را تکمیل کنید.");
      return;
    }

    if (
      formData.preferredStartTime &&
      formData.preferredEndTime &&
      formData.preferredStartTime >= formData.preferredEndTime
    ) {
      setError("زمان پایان باید بعد از زمان شروع باشد.");
      return;
    }

    setError("");
    onSearch({
      ...formData,
      equipment: selectedEquipment,
      injuries: selectedInjuries,
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <p className="text-[#185E64] text-lg">در حال بارگذاری...</p>
      </div>
    );
  }

  return (
    <div className="bg-[#D9D9D9] rounded-3xl p-8 shadow-2xl">
      {error && (
        <div className="mb-6 rounded-xl bg-red-50 text-red-700 p-4 text-sm border border-red-200">
          {error}
        </div>
      )}

      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-2">
              هدف ورزشی
            </label>
            <select
              className="w-full px-4 py-2.5 border border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-[#185E64]"
              name="goalId"
              value={formData.goalId}
              onChange={handleChange}
            >
              <option value="">انتخاب هدف</option>
              {goals.map((goal) => (
                <option key={goal.id} value={goal.id}>
                  {goal.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-2">
              سطح آمادگی
            </label>
            <select
              className="w-full px-4 py-2.5 border border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-[#185E64]"
              name="fitnessLevel"
              value={formData.fitnessLevel}
              onChange={handleChange}
            >
              <option value="">انتخاب سطح</option>
              {options.fitnessLevels.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-2">
              نوع تمرین
            </label>
            <select
              className="w-full px-4 py-2.5 border border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-[#185E64]"
              name="workoutType"
              value={formData.workoutType}
              onChange={handleChange}
            >
              <option value="">انتخاب نوع</option>
              {options.workoutTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-2">
              زمان شروع
            </label>
            <input
              type="time"
              name="preferredStartTime"
              value={formData.preferredStartTime}
              onChange={handleChange}
              step="60"
              className="w-full px-4 py-2.5 border border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-[#185E64]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-2">
              زمان پایان
            </label>
            <input
              type="time"
              name="preferredEndTime"
              value={formData.preferredEndTime}
              onChange={handleChange}
              step="60"
              className="w-full px-4 py-2.5 border border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-[#185E64]"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSubmit}
              className="w-full bg-[#FDE6C3] hover:bg-[#f5d4a8] text-[#185E64] font-bold py-2.5 px-4 rounded-xl transition-colors duration-200 border border-[#185E64] border-opacity-15 shadow-md hover:shadow-lg text-base"
            >
              جستجوی گروه
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-4 border-t border-[#BCDADD] border-opacity-50">
          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-3">
              روزهای تمرین
            </label>
            <div className="grid grid-cols-2 gap-2">
              {days.map((day) => (
                <label
                  key={day}
                  className="flex items-center gap-2 text-sm text-[#185E64] cursor-pointer hover:opacity-70 transition-opacity"
                >
                  <input
                    type="checkbox"
                    checked={formData.availableDays.includes(day)}
                    onChange={() => toggleDay(day)}
                    className="w-4 h-4 border border-[#185E64] rounded focus:ring-[#FDE6C3] bg-white"
                  />
                  {dayLabelsFa[day] || day}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-3">
              تجهیزات در دسترس
            </label>
            <div className="grid grid-cols-2 gap-2">
              {equipment.map((item) => (
                <label
                  key={item.id}
                  className="flex items-center gap-2 text-sm text-[#185E64] cursor-pointer hover:opacity-70 transition-opacity"
                >
                  <input
                    type="checkbox"
                    checked={selectedEquipment.includes(item.id)}
                    onChange={() => toggleEquipment(item.id)}
                    className="w-4 h-4 border border-[#185E64] rounded focus:ring-[#FDE6C3] bg-white"
                  />
                  {item.name}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#185E64] mb-3">
              سابقه آسیب
            </label>

            {hasInjuryHistory ? (
              <div className="bg-[#CDF1F4] bg-opacity-30 rounded-xl p-4">
                <p className="text-sm text-[#185E64] font-medium mb-2">
                  آسیب‌های ثبت شده:
                </p>
                <ul className="space-y-1.5">
                  {userInjuries.map((injury, index) => (
                    <li key={index} className="text-sm text-[#185E64]">
                      {injury.name || injury}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-[#185E64] text-opacity-70 mt-2">
                  برای تغییر به پروفایل مراجعه کنید
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-[#185E64] text-opacity-80 mb-2">
                  آسیب‌ها را انتخاب کنید:
                </p>
                <div className="grid grid-cols-1 gap-1.5 max-h-32 overflow-y-auto pr-1">
                  {injuryOptions.map((injury) => (
                    <label
                      key={injury.id}
                      className="flex items-center gap-2 text-sm text-[#185E64] cursor-pointer hover:opacity-70 transition-opacity"
                    >
                      <input
                        type="checkbox"
                        checked={selectedInjuries.includes(injury.id)}
                        onChange={() => toggleInjury(injury.id)}
                        className="w-4 h-4 border border-[#185E64] rounded focus:ring-[#FDE6C3] bg-white"
                      />
                      {injury.name}
                    </label>
                  ))}
                </div>
                {selectedInjuries.length === 0 && (
                  <p className="text-sm text-[#185E64] mt-2 font-medium">
                    شما سالم هستید
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default FilterPanel;
