import { useState, useEffect } from "react";

function FilterPanel({ onSearch, onJoinGroup }) {
  const [formData, setFormData] = useState({
    goalId: "",
    fitnessLevel: "",
    workoutType: "",
    availableDays: [],
    preferredStartTime: "",
    preferredEndTime: "",
  });

  const [options, setOptions] = useState({
    fitnessLevels: [],
    workoutTypes: [],
  });

  const [goals, setGoals] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [injuryOptions, setInjuryOptions] = useState([]);
  const [userInjuries, setUserInjuries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEquipment, setSelectedEquipment] = useState([]);
  const [selectedInjuries, setSelectedInjuries] = useState([]);
  const [hasInjuryHistory, setHasInjuryHistory] = useState(false);

  const days = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
  ];

  const fetchWithAuth = async (url) => {
    const token = localStorage.getItem("token");
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    return response.json();
  };

  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const [optionsData, goalsData, equipmentData, injuryOptionsData, profileData] = await Promise.all([
          fetchWithAuth("/api/options"),
          fetchWithAuth("/api/goals"),
          fetchWithAuth("/api/equipment"),
          fetchWithAuth("/api/injury-options"),
          fetchWithAuth("/api/profile"),
        ]);

        if (optionsData.success) {
          setOptions({
            fitnessLevels: optionsData.data.fitness_levels || [],
            workoutTypes: optionsData.data.workout_types || [],
          });
        }

        if (goalsData.success) {
          setGoals(goalsData.data.goals || []);
        }

        if (equipmentData.success) {
          setEquipment(equipmentData.data.equipment || []);
        }

        if (injuryOptionsData.success) {
          setInjuryOptions(injuryOptionsData.data.injuries || []);
        }

        if (profileData.success) {
          const injuriesList = profileData.data.profile.injury_history || [];
          setUserInjuries(injuriesList);
          
          if (injuriesList.length > 0) {
            setHasInjuryHistory(true);
            setSelectedInjuries(injuriesList.map(injury => injury.id || injury));
          }
        }

        setLoading(false);
      } catch (err) {
        setError("خطا در دریافت اطلاعات");
        setLoading(false);
      }
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
        : [...prev, equipId]
    );
  };

  const toggleInjury = (injuryId) => {
    setSelectedInjuries((prev) =>
      prev.includes(injuryId)
        ? prev.filter((id) => id !== injuryId)
        : [...prev, injuryId]
    );
  };

  const handleSubmit = () => {
    if (!formData.goalId || !formData.fitnessLevel || !formData.workoutType) {
      setError("لطفاً تمام فیلدهای ضروری را تکمیل کنید.");
      return;
    }

    setError("");
    const searchData = {
      ...formData,
      equipment: selectedEquipment,
      injuries: selectedInjuries,
    };
    onSearch(searchData);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-[#185E64] text-lg">⏳ در حال بارگذاری...</div>
      </div>
    );
  }

  return (
    <div className="bg-[#185E64] rounded-3xl p-8 shadow-2xl">
      {error && (
        <div className="mb-6 rounded-xl bg-red-100 text-red-700 p-4 text-sm border-2 border-red-200 flex items-center gap-2">
          <span>⚠️</span>
          {error}
        </div>
      )}

      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-5">
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              🎯 هدف ورزشی
            </label>
            <select
              className="w-full px-4 py-2.5 border-2 border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-gray-700"
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
            <label className="block text-sm font-medium text-white mb-2">
              💪 سطح آمادگی
            </label>
            <select
              className="w-full px-4 py-2.5 border-2 border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-gray-700"
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
            <label className="block text-sm font-medium text-white mb-2">
              🏋️ نوع تمرین
            </label>
            <select
              className="w-full px-4 py-2.5 border-2 border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-gray-700"
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

        <div className="grid grid-cols-3 gap-5">
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              🕐 زمان شروع
            </label>
            <input
              type="time"
              name="preferredStartTime"
              value={formData.preferredStartTime}
              onChange={handleChange}
              step="60"
              className="w-full px-4 py-2.5 border-2 border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-gray-700"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-2">
              🕐 زمان پایان
            </label>
            <input
              type="time"
              name="preferredEndTime"
              value={formData.preferredEndTime}
              onChange={handleChange}
              step="60"
              className="w-full px-4 py-2.5 border-2 border-[#BCDADD] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#FDE6C3] focus:border-transparent bg-white text-sm text-gray-700"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSubmit}
              className="w-full bg-[#FDE6C3] hover:bg-[#f5d4a8] text-[#185E64] font-bold py-2.5 px-4 rounded-xl transition-all duration-200 border-2 border-white border-opacity-30 shadow-lg hover:shadow-xl text-base flex items-center justify-center gap-2"
            >
              <span>🔍</span>
              جستجوی گروه
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 pt-4 border-t-2 border-[#BCDADD] border-opacity-30">
          <div>
            <label className="block text-sm font-medium text-white mb-3">
              📅 روزهای تمرین
            </label>
            <div className="grid grid-cols-2 gap-2">
              {days.map((day) => (
                <label key={day} className="flex items-center gap-2 text-sm text-white cursor-pointer hover:text-[#FDE6C3] transition-colors">
                  <input
                    type="checkbox"
                    checked={formData.availableDays.includes(day)}
                    onChange={() => toggleDay(day)}
                    className="w-4 h-4 text-[#FDE6C3] border-2 border-white rounded focus:ring-[#FDE6C3] bg-white bg-opacity-20"
                  />
                  {day}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-3">
              🏋️ تجهیزات در دسترس
            </label>
            <div className="grid grid-cols-2 gap-2">
              {equipment.map((item) => (
                <label key={item.id} className="flex items-center gap-2 text-sm text-white cursor-pointer hover:text-[#FDE6C3] transition-colors">
                  <input
                    type="checkbox"
                    checked={selectedEquipment.includes(item.id)}
                    onChange={() => toggleEquipment(item.id)}
                    className="w-4 h-4 text-[#FDE6C3] border-2 border-white rounded focus:ring-[#FDE6C3] bg-white bg-opacity-20"
                  />
                  {item.name}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-3">
              🩺 سابقه آسیب
            </label>
            
            {hasInjuryHistory ? (
              <div className="bg-white bg-opacity-10 rounded-xl p-4 backdrop-blur-sm">
                <p className="text-sm text-white font-medium mb-2 flex items-center gap-2">
                  <span>📋</span> آسیب‌های ثبت شده:
                </p>
                <ul className="space-y-1.5">
                  {userInjuries.map((injury, index) => (
                    <li key={index} className="text-sm text-white flex items-center gap-2">
                      <span>🔴</span>
                      {injury.name || injury}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-white text-opacity-70 mt-2 flex items-center gap-1">
                  <span>💡</span> برای تغییر به پروفایل مراجعه کنید
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-white text-opacity-90 mb-2 flex items-center gap-1">
                  <span>🤔</span> آسیب‌ها را انتخاب کنید:
                </p>
                <div className="grid grid-cols-1 gap-1.5 max-h-32 overflow-y-auto pr-1">
                  {injuryOptions.map((injury) => (
                    <label key={injury.id} className="flex items-center gap-2 text-sm text-white cursor-pointer hover:text-[#FDE6C3] transition-colors">
                      <input
                        type="checkbox"
                        checked={selectedInjuries.includes(injury.id)}
                        onChange={() => toggleInjury(injury.id)}
                        className="w-4 h-4 text-[#FDE6C3] border-2 border-white rounded focus:ring-[#FDE6C3] bg-white bg-opacity-20"
                      />
                      {injury.name}
                    </label>
                  ))}
                </div>
                {selectedInjuries.length === 0 && (
                  <p className="text-sm text-green-300 mt-2 flex items-center gap-1">
                    <span>✅</span> شما سالم هستید
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