function FilterPanel() {
  return (
    <div>
      <h2 className="text-xl font-bold mb-5 text-center">
        اطلاعات شما
      </h2>

      <div className="space-y-4">

        <div>
          <label className="block mb-1">هدف ورزشی</label>
          <select className="w-full border rounded p-2">
            <option>انتخاب کنید</option>
          </select>
        </div>

        <div>
          <label className="block mb-1">سطح آمادگی</label>
          <select className="w-full border rounded p-2">
            <option>انتخاب کنید</option>
          </select>
        </div>

        <div>
          <label className="block mb-1">
            محدودیت جسمانی
          </label>

          <input
            className="w-full border rounded p-2"
            placeholder="مثلا زانو درد"
          />
        </div>

        <div>
          <label className="block mb-1">
            نوع تمرین
          </label>

          <select className="w-full border rounded p-2">
            <option>انتخاب کنید</option>
          </select>
        </div>

        <div>
          <label className="block mb-1">
            زمان موردنظر
          </label>

          <select className="w-full border rounded p-2">
            <option>انتخاب کنید</option>
          </select>
        </div>

        <button className="w-full bg-blue-600 text-white rounded py-2 hover:bg-blue-700">
          دریافت پیشنهاد
        </button>

      </div>
    </div>
  );
}

export default FilterPanel;