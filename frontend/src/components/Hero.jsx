import yogaImage from '../assets/img/yoga.jpeg';

export default function Hero() {
  return (
    <section className="relative w-full min-h-screen bg-[#185E64]">
      <img 
        src={yogaImage} 
        alt="Hero"
        className="absolute inset-0 w-full h-full object-cover object-center"
      />
      <div className="absolute inset-0 bg-black/20"></div>
      
      {/* افزایش فاصله از راست و چپ: px-12 به px-16 و اضافه کردن mx-auto */}
      <div className="relative z-10 flex flex-col items-end justify-center h-full text-right px-16 md:px-20 lg:px-28 pt-32">
        
        {/* پلی‌لایف - کرم */}
        <h1 className="text-[#FCF6ED] text-5xl md:text-6xl font-extrabold mb-1">
          پلی‌لایف
        </h1>
        
        {/* !یک اپلیکیشن */}
        <div className="text-5xl md:text-6xl font-extrabold mb-1">
          <span className="text-black">!یک </span>
          <span className="text-[#FCF6ED]">اپلیکیشن</span>
        </div>
        
        {/* یک سبک زندگی کامل */}
        <h1 className="text-black text-5xl md:text-6xl font-extrabold mb-8">
          یک سبک زندگی کامل
        </h1>
        
        {/* متن ماموریت - حداکثر عرض بیشتر */}
        <p className="text-white text-base md:text-lg max-w-2xl mb-2 leading-relaxed">
          ماموریت پلی‌لایف توانمندسازی افراد برای ساختن بهترین نسخه از خودشان است.
        </p>
        
        {/* متن توضیحی - حداکثر عرض بیشتر */}
        <p className="text-white/85 text-sm md:text-base max-w-2xl leading-relaxed mb-8">
          ما اینجا هستیم تا با تلفیق برنامه‌های تمرینی، رژیم‌های شخصی‌سازی شده و قدرت یک شبکه اجتماعی حامی، 
          تناسب اندام را از یک چالش خسته کننده به یک سبک زندگی پایدار و کامل تبدیل کنیم.
        </p>

        {/* فرم شماره تلفن */}
        <div className="w-full max-w-md">
          <div className="bg-[#D9D9D9] rounded-full py-3 px-4 flex items-center justify-between gap-2">
            <div className="bg-[#185E64] rounded-full px-8 py-3 whitespace-nowrap">
              <span className="text-white font-bold text-base">شروع کنید</span>
            </div>
            <div className="flex items-center gap-2 text-right px-2">
              <span className="text-[#FCF6ED]/70 text-sm">شماره تماست رو وارد کن</span>
              <svg className="w-5 h-5 text-[#FCF6ED]/70" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/>
              </svg>
            </div>
          </div>
        </div>

        {/* بخش مورد اعتماد مربیان */}
        <div className="mt-8 w-full max-w-md mr-1">
          <div className="flex justify-end">
            <div className="flex -space-x-3">
              <div className="w-9 h-9 rounded-full bg-gray-300 border-2 border-white overflow-hidden">
                <img src="https://randomuser.me/api/portraits/women/1.jpg" alt="مربی" className="w-full h-full object-cover" />
              </div>
              <div className="w-9 h-9 rounded-full bg-gray-300 border-2 border-white overflow-hidden">
                <img src="https://randomuser.me/api/portraits/men/2.jpg" alt="مربی" className="w-full h-full object-cover" />
              </div>
              <div className="w-9 h-9 rounded-full bg-gray-300 border-2 border-white overflow-hidden">
                <img src="https://randomuser.me/api/portraits/women/3.jpg" alt="مربی" className="w-full h-full object-cover" />
              </div>
              <div className="w-9 h-9 rounded-full bg-gray-300 border-2 border-white overflow-hidden">
                <img src="https://randomuser.me/api/portraits/men/4.jpg" alt="مربی" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
          <div className="text-right mt-2">
            <span className="text-white/70 text-xs">مورد اعتماد بیش از ۱۰۰۰ مربی سلامت</span>
          </div>
        </div>
      </div>
    </section>
  );
}