import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import React from 'react';
import { useState, useEffect } from 'react';
import StatsSection from '../components/StatsSection';
import oneImage from '../assets/img/one.png';
import twoImage from '../assets/img/two.png';
import HandshakeIcon from '../assets/img/handshake-svgrepo-com.svg';
import RobotIcon from '../assets/img/robot-children-metal-svgrepo-com.svg';
import NetworkIcon from '../assets/img/network-3-round-1083-svgrepo-com.svg';
import PuzzleIcon from '../assets/img/puzzle-9-svgrepo-com.svg';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#185E64] to-[#2a8e96]">
      <Navbar />
      <Hero />
      
      {/* StatsSection - با انیمیشن شمارش اعداد */}
      <StatsSection />
      
{/* اکوسیستم هوشمند - مدار دایره‌ای */}
      <section className="py-20 px-8 overflow-visible">
        <h2 className="text-3xl font-bold text-white text-center mb-16">اکوسیستم هوشمند پلی‌لایف</h2>
        
        <div className="relative max-w-7xl mx-auto min-h-[950px] overflow-visible">
          
          {/* دایره‌های پس‌زمینه متحرک */}
          <div className="absolute inset-0 flex items-center justify-center overflow-visible">
            <div className="w-[750px] h-[750px] rounded-full border border-white/10 animate-pulse"></div>
            <div className="absolute w-[850px] h-[850px] rounded-full border border-white/5 animate-pulse delay-1000"></div>
            <div className="absolute w-[650px] h-[650px] rounded-full border border-white/20"></div>
          </div>
          
          {/* هسته مرکزی PolyLife */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
            <div className="w-56 h-56 bg-gradient-to-br from-[#185E64] to-[#2a8e96] rounded-full flex items-center justify-center shadow-2xl border-2 border-[#FDE6C3] transition-all duration-300 hover:scale-105">
              <h3 className="text-white font-bold text-3xl text-center">PolyLife</h3>
            </div>
          </div>
          
          {/* میکروسرویس‌ها */}
          {(() => {
            const services = [
              { name: "PolyDiet", icon: "🥗", angle: 0, fullDesc: "مدیریت رژیم غذایی و کالری شمار | برنامه غذایی شخصی‌سازی شده با هوش مصنوعی" },
              { name: "PolyWorkout", icon: "💪", angle: 45, fullDesc: "برنامه‌های تمرینی هوشمند | تمرینات اختصاصی بر اساس سطح آمادگی" },
              { name: "PolyChallenge", icon: "🏆", angle: 90, fullDesc: "چالش‌های گروهی | مسابقات آنلاین با دوستان و جایزه" },
              { name: "PolyShop", icon: "🛒", angle: 135, fullDesc: "فروشگاه تجهیزات و مکمل | خرید آنلاین با تخفیف ویژه کاربران" },
              { name: "PolyAnalysis", icon: "📈", angle: 180, fullDesc: "تحلیل پیشرفت و آنالیز بدن | نمودارهای تغییرات وزن و حجم عضلات" },
              { name: "PolySocial", icon: "👥", angle: 225, fullDesc: "شبکه اجتماعی ورزشکاران | اشتراک‌گذاری دستاوردها و ارتباط با حرفه‌ای‌ها" },
              { name: "PolyProgress", icon: "📊", angle: 270, fullDesc: "پیگیری پیشرفت و سیستم یادآور | یادآور هوشمند تمرین و وعده‌های غذایی" },
              { name: "PolyGroupie", icon: "🤝", angle: 315, fullDesc: "پیشنهاد تمرین گروهی | پیدا کردن هم‌تمرین مناسب و آنالیز ریسک آسیب" }
            ];
            
            const radius = 380;
            const [hoveredService, setHoveredService] = React.useState(null);
            
            return (
              <>
                {services.map((service) => {
                  const angle = service.angle;
                  const x = Math.cos((angle * Math.PI) / 180) * radius;
                  const y = Math.sin((angle * Math.PI) / 180) * radius;
                  const lineAngle = (angle + 180) % 360;
                  
                  return (
                    <div
                      key={service.name}
                      className="absolute group"
                      onMouseEnter={() => setHoveredService(service)}
                      onMouseLeave={() => setHoveredService(null)}
                      style={{
                        left: `calc(50% + ${x}px)`,
                        top: `calc(50% + ${y}px)`,
                        transform: "translate(-50%, -50%)",
                        zIndex: 30
                      }}
                    >
                      {/* مربع اصلی */}
                      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 text-white text-center transition-all duration-300 hover:scale-110 hover:bg-white/20 hover:shadow-2xl cursor-pointer border border-white/20 hover:border-[#FDE6C3] min-w-[200px] relative z-10">
                        <div className="text-5xl mb-3 transition-transform duration-300 group-hover:scale-125">
                          {service.icon}
                        </div>
                        <h3 className="font-bold text-lg group-hover:text-[#FDE6C3]">
                          {service.name}
                        </h3>
                      </div>
                      
                      {/* خط نورانی */}
                      <div 
                        className="absolute h-0.5 bg-gradient-to-r from-[#FDE6C3] via-[#FDE6C3]/70 to-transparent origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500"
                        style={{
                          width: `220px`,
                          top: '50%',
                          left: '50%',
                          transform: `translate(0, -50%) rotate(${lineAngle}deg)`,
                          transformOrigin: 'left center'
                        }}
                      ></div>
                    </div>
                  );
                })}
                
{/* مربع توضیحات وسط صفحه - خیلی روشن با متن تیره */}
<div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none">
  <div 
    className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-2xl border border-[#185E64]/20 w-96 transition-all duration-300 ${
      hoveredService ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
    }`}
  >
    {hoveredService && (
      <>
        <div className="flex items-center gap-3 mb-3">
          <div className="text-4xl">{hoveredService.icon}</div>
          <h4 className="text-[#185E64] font-bold text-xl">{hoveredService.name}</h4>
        </div>
        <p className="text-[#185E64]/80 text-sm leading-relaxed">
          {hoveredService.fullDesc}
        </p>
      </>
    )}
  </div>
</div>
              </>
            );
          })()}
          
        </div>
      </section>

      {/* بخش اول: سبک زندگی سالم */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 py-16">
        <div className="bg-[#FAEEDB] rounded-3xl p-6 sm:p-12">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="md:w-1/2 flex justify-center -mt-8 md:-mt-12">
              <img src={oneImage} alt="سبک زندگی سالم" className="w-64 sm:w-72 h-auto object-cover rounded-2xl" />
            </div>
            <div className="md:w-1/2 text-right">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-[#032F34] mb-12">سبک زندگی سالم در یک مکان</h2>
              <p className="text-[#032F34] leading-relaxed text-sm sm:text-base mb-6">
                پلی‌لایف جایی است که مسیر رسیدن به تناسب اندام، سلامتی و شادابی دیگر یک مسیر سخت و پراکنده نیست. 
                ما می‌دانیم که داشتن یک سبک زندگی سالم، نیازمند تمرین درست، تغذیه اصولی، انگیزه مداوم و دسترسی به امکانات استاندارد است. 
                در گذشته برای مدیریت هرکدام از این موارد به یک اپلیکیشن جداگانه یا مراجعه به چندین متخصص نیاز داشتید؛ 
                اما ما در پلی‌لایف همه‌چیز را زیر یک سقف جمع کرده‌ایم.
              </p>
              
              <div className="flex flex-col md:flex-row md:justify-end md:space-x-20 space-y-3 md:space-y-0 mt-10">
                <div className="flex items-center justify-end gap-2 text-[#032F34] text-sm sm:text-base">
                  <span className="text-black text-base sm:text-lg">✓</span>
                  <span className="whitespace-nowrap">تمرین صحیح و اصولی</span>
                </div>
                <div className="flex items-center justify-end gap-2 text-[#032F34] text-sm sm:text-base">
                  <span className="text-black text-base sm:text-lg">✓</span>
                  <span className="whitespace-nowrap">تغذیه متناسب با اهداف شما</span>
                </div>
                <div className="flex items-center justify-end gap-2 text-[#032F34] text-sm sm:text-base">
                  <span className="text-black text-base sm:text-lg">✓</span>
                  <span className="whitespace-nowrap">انگیزه و پشتیبانی مداوم</span>
                </div>
                <div className="flex items-center justify-end gap-2 text-[#032F34] text-sm sm:text-base">
                  <span className="text-black text-base sm:text-lg">✓</span>
                  <span className="whitespace-nowrap">همه‌چیز زیر یک سقف</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* بخش دوم: اکوسیستم هوشمند (متن) */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 py-16">
        <div className="bg-[#09575F] rounded-3xl p-6 sm:p-12">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="md:w-1/2 text-center md:text-left order-2 md:order-1">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-[#FFF0D8] mb-12">اکوسیستم هوشمند پلی‌لایف</h2>
              <p className="text-[#FFF0D8]/80 leading-relaxed text-sm sm:text-base">
                پلی‌لایف صرفاً یک اپلیکیشن ورزشی نیست؛ بلکه یک اکوسیستم هوشمند و همه‌جانبه است که از کنار هم قرار گرفتن سرویس‌های تخصصی ساخته شده است. 
                هر بخش از این سیستم برای پاسخ به یکی از نیازهای شما طراحی شده و در نهایت، همه با هم یک تجربه یکپارچه و منسجم را برایتان رقم می‌زنند.
              </p>
            </div>
            <div className="md:w-1/2 flex justify-center order-1 md:order-2">
              <img src={twoImage} alt="اکوسیستم هوشمند" className="w-80 sm:w-96 h-auto object-cover rounded-2xl" />
            </div>
          </div>
        </div>
      </section>

{/* چرا پلی‌لایف؟ - اسلایدر خودکار با 6 کارت و انیمیشن ملایم */}
<section className="max-w-6xl mx-auto px-4 sm:px-8 py-16">
  
  <div className="w-full flex justify-center mb-8">
    <div className="w-full max-w-4xl h-px bg-[#EBD9BC]"></div>
  </div>
  
  <div className="text-center mb-12">
    <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white">چرا پلی‌لایف؟</h2>
  </div>
  
  {(() => {
    // لیست 6 کارت
    const allCards = [
      {
        icon: <img src={PuzzleIcon} alt="یکپارچگی" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "یکپارچگی کامل ",
        desc: "همگام‌سازی خودکار بین رژیم، تمرین و خریدها."
      },
      {
        icon: <img src={NetworkIcon} alt="معماری میکروسرویس" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "معماری میکروسرویس ",
        desc: "سرعت بالا، پایداری و امنیت داده‌های شما در ابعاد بزرگ."
      },
      {
        icon: <img src={RobotIcon} alt="هوش مصنوعی" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "هوش مصنوعی اختصاصی ",
        desc: "تحلیل دقیق فرم بدن و ارائه برنامه شخصی‌سازی شده."
      },
      {
        icon: <img src={HandshakeIcon} alt="جامعه پویا" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "جامعه‌ای پویا و حامی ",
        desc: "جامعه‌ای فعال که کاربر را در مسیر اهداف همراهی و حمایت می‌کند."
      },
      {
        icon: <img src={PuzzleIcon} alt="پشتیبانی" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "پشتیبانی ۲۴/۷ ",
        desc: "تیم پشتیبانی همیشه در دسترس برای پاسخگویی به سوالات شما."
      },
      {
        icon: <img src={NetworkIcon} alt="امنیت" className="w-10 h-10" style={{ filter: 'invert(15%) sepia(91%) saturate(1000%) hue-rotate(150deg) brightness(30%)' }} />,
        title: "امنیت بالا ",
        desc: "حفاظت از اطلاعات شخصی و حریم خصوصی کاربران."
      }
    ];

    const [visibleCards, setVisibleCards] = useState(allCards.slice(0, 4));
    const [currentIndex, setCurrentIndex] = useState(4);
    const [isTransitioning, setIsTransitioning] = useState(false);

    useEffect(() => {
      const interval = setInterval(() => {
        setIsTransitioning(true);
        
        setTimeout(() => {
          setVisibleCards(prev => {
            const newCards = [...prev];
            newCards.shift();
            newCards.push(allCards[currentIndex % allCards.length]);
            return newCards;
          });
          setCurrentIndex(prev => prev + 1);
          setIsTransitioning(false);
        }, 300);
      }, 3000); // هر 3 ثانیه

      return () => clearInterval(interval);
    }, [currentIndex]);

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        {visibleCards.map((card, idx) => (
          <div 
            key={idx} 
            className={`
              bg-[#EBD9BC]/60 rounded-2xl p-6 text-center backdrop-blur-sm 
              transition-all duration-500 ease-in-out hover:scale-105 hover:shadow-xl
              ${isTransitioning ? 'opacity-0 translate-y-4' : 'opacity-100 translate-y-0'}
            `}
          >
            <div className="flex justify-center mb-4 transition-transform duration-300 hover:scale-110">
              {card.icon}
            </div>
            <h3 className="text-xl font-bold text-[#032F34] mb-3">{card.title}</h3>
            <p className="text-[#032F34]/80 text-sm leading-relaxed">{card.desc}</p>
          </div>
        ))}
      </div>
    );
  })()}
  
  <div className="w-full flex justify-center mt-12">
    <div className="w-full max-w-4xl h-px bg-[#EBD9BC]"></div>
  </div>
</section>

      {/* چشم‌انداز ما - با انیمیشن محو شدن هنگام اسکرول */}
      <section className="max-w-4xl mx-auto px-4 sm:px-8 py-16 text-center">
        <div
          className="transition-all duration-1000 ease-out"
          style={{
            opacity: 0,
            transform: 'translateY(30px)',
            animation: 'fadeInUp 0.8s ease-out forwards',
            animationPlayState: 'paused'
          }}
          ref={(el) => {
            if (!el) return;
            const observer = new IntersectionObserver(
              ([entry]) => {
                if (entry.isIntersecting) {
                  el.style.animationPlayState = 'running';
                  observer.disconnect();
                }
              },
              { threshold: 0.3 }
            );
            observer.observe(el);
          }}
        >
          <style>{`
            @keyframes fadeInUp {
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }
          `}</style>
          
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-8">چشم‌انداز ما</h2>
          <p className="text-white/80 text-base sm:text-lg leading-relaxed">
            ما در پلی‌لایف معتقدیم که سلامتی، یک پارادایم چندبعدی است. هدف ما این است که با ادغام تکنولوژی روز، 
            دانش متخصصان و قدرت یک جامعه فعال، فاصله‌ی میان «خواستن» و «توانستن» را از بین ببریم.
            <br /><br />
            با پلی‌لایف، بهانه‌ها تمام می‌شود و تغییر آغاز می‌گردد. سبک سالم خودت رو بساز!
          </p>
        </div>
      </section>

      {/* فوتر */}
      <footer className="bg-[#FAEEDB] mt-24 py-12 px-4 sm:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div className="text-center md:text-left">
              <p className="text-[#032F34] text-lg mb-4">پاسخگوی سوالات شما هستیم :</p>
              <div className="flex flex-col sm:flex-row justify-center md:justify-start gap-4 text-[#032F34] text-base">
                <span>021-112234</span>
                <span className="hidden sm:inline">|</span>
                <span>021-112233</span>
              </div>
              <p className="text-[#032F34]/60 text-sm mt-8">ما را در شبکه‌های اجتماعی دنبال کنید!</p>
            </div>
            
            <div className="text-right">
              <div className="grid grid-cols-2 gap-x-16 gap-y-10">
                <div className="space-y-10">
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">پرسش‌های متداول</a>
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">خدمات ما</a>
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">آدرس</a>
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">پشتیبانی</a>
                </div>
                <div className="space-y-10">
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">تماس با ما</a>
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">درباره ما</a>
                  <a href="#" className="text-[#032F34] hover:text-[#185E64] transition text-sm block">شرایط و قوانین</a>
                </div>
              </div>
            </div>
          </div>
          
          <div className="w-full h-px bg-[#032F34]/20 my-8"></div>
          
          <div className="text-center text-[#032F34]/60 text-xs">
            <p>© 2026 PolyLife - تمامی حقوق محفوظ است</p>
          </div>
        </div>
      </footer>
    </div>
  );
}