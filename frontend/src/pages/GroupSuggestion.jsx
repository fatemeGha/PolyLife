import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import GroupList from "../components/groupSuggestion/GroupList";
import FilterPanel from "../components/groupSuggestion/FilterPanel";

function GroupSuggestion() {
  return (
    <>
      <Navbar />

      <main className="container mx-auto p-6">
        <section className="text-center mb-8">
          <h1 className="text-3xl font-bold">پیشنهاد گروه تمرینی</h1>

          <p className="text-gray-600 mt-2">
            اطلاعات خود را وارد کنید تا گروه مناسب به شما پیشنهاد شود.
          </p>
        </section>

        <div className="grid grid-cols-3 gap-6">
          <div className="border rounded-lg p-4">
                <FilterPanel />
          </div>

          <div className="col-span-2 border rounded-lg p-4">
                <GroupList />
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
export default GroupSuggestion;
