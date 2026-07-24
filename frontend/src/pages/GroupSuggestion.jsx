import { useState } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import GroupList from "../components/groupSuggestion/GroupList";
import FilterPanel from "../components/groupSuggestion/FilterPanel";

function GroupSuggestion() {
  const [showGroups, setShowGroups] = useState(false);
  const [searchParams, setSearchParams] = useState(null);
  const [groupCount, setGroupCount] = useState(0);
  const [joinNotice, setJoinNotice] = useState("");

  const handleSearch = (data) => {
    setSearchParams(data);
    setShowGroups(true);
  };

  const handleJoinGroup = () => {
    setJoinNotice("عضویت شما با موفقیت ثبت شد.");
    setTimeout(() => setJoinNotice(""), 4000);
  };

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-[#185E64] px-8 pt-28 pb-12">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <h1
              className="text-5xl font-bold text-white mb-3"
              style={{ fontFamily: "'Abril Fatface', serif" }}
            >
              PolyLife
            </h1>
            <p className="text-[#CDF1F4] text-lg">
              پیشنهاد گروه تمرینی مناسب برای شما
            </p>
          </div>

          <FilterPanel onSearch={handleSearch} />

          {joinNotice && (
            <div className="mt-6 bg-[#FDE6C3] text-[#185E64] font-semibold px-5 py-3 rounded-xl shadow-md text-center">
              {joinNotice}
            </div>
          )}

          {showGroups && (
            <div className="mt-8">
              <div className="flex justify-between items-center mb-5">
                <h2 className="text-2xl font-bold text-white">
                  گروه‌های پیشنهادی
                </h2>
                <span className="bg-[#FDE6C3] text-[#185E64] px-5 py-2 rounded-full text-sm font-bold shadow-md">
                  {groupCount} گروه
                </span>
              </div>

              <div className="bg-[#D9D9D9] rounded-3xl shadow-2xl p-6">
                <GroupList
                  filters={searchParams}
                  onJoinGroup={handleJoinGroup}
                  onGroupsLoaded={setGroupCount}
                />
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