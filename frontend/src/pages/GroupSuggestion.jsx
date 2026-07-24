import { useState } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import GroupList from "../components/groupSuggestion/GroupList";
import FilterPanel from "../components/groupSuggestion/FilterPanel";

function GroupSuggestion() {
  const [showGroups, setShowGroups] = useState(false);
  const [searchParams, setSearchParams] = useState(null);

  const handleSearch = (data) => {
    setSearchParams(data);
    setShowGroups(true);
  };

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-[#185E64] px-8 pt-28 pb-12">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-bold text-white mb-3" style={{ fontFamily: "'Abril Fatface', serif" }}>
              🏋️ PolyLife
            </h1>
            
            <p className="text-[#CDF1F4] text-lg flex items-center justify-center gap-2">
              <span>✨</span>
              پیشنهاد گروه تمرینی مناسب برای شما
              <span>✨</span>
            </p>
          </div>

          <FilterPanel onSearch={handleSearch} />

          {showGroups && (
            <div className="mt-8">
              <div className="flex justify-between items-center mb-5">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  <span>📋</span> گروه‌های پیشنهادی
                </h2>
                <span className="bg-[#FDE6C3] text-[#185E64] px-5 py-2 rounded-full text-sm font-bold shadow-lg flex items-center gap-2">
                  <span>🔢</span> ۱۲ گروه
                </span>
              </div>
              
              <div className="bg-white rounded-3xl shadow-2xl p-6">
                <GroupList searchParams={searchParams} />
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}

export default GroupSuggestion;