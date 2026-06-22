// src/components/StatsSection.jsx
import { useState, useEffect, useRef } from 'react';

const useCountUp = (end, duration = 1.5, suffix = '') => {  // duration از 2.5 به 1.5 تغییر کرد
  const [count, setCount] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const elementRef = useRef(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          setIsVisible(true);
          hasAnimated.current = true;
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    if (elementRef.current) {
      observer.observe(elementRef.current);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isVisible) return;

    let startTime;
    let animationFrame;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const currentCount = Math.floor(progress * end);
      setCount(currentCount);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      } else {
        setCount(end);
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isVisible, end, duration]);

  return { count, suffix, elementRef };
};

const StatsSection = () => {
  const stats = [
    { icon: "🎧", value: 24, suffix: "/7", label: "پشتیبانی اختصاصی" },
    { icon: "🔥", value: 10000, suffix: "+", label: "کالری سوزانده شده" },
    { icon: "📋", value: 100, suffix: "+", label: "برنامه تمرینی هوشمند" },
    { icon: "👤", value: 50, suffix: "+", label: "مربی متخصص" }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 px-12 py-10 my-10 max-w-6xl mx-auto overflow-hidden">
      {stats.map((stat, index) => {
        const { count, suffix, elementRef } = useCountUp(stat.value, 1.5, stat.suffix);
        
        return (
          <div
            key={index}
            ref={elementRef}
            className="text-center relative group"
            style={{
              opacity: 0,
              transform: 'translateY(30px)',
              animation: `fadeInUp 0.4s ease-out ${index * 0.1}s forwards`,
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
            
            <div className="text-5xl mb-3 transition-transform duration-300 group-hover:scale-110">
              {stat.icon}
            </div>
            
            <div className="text-3xl md:text-4xl font-bold text-white">
              {count}{suffix}
            </div>
            
            <div className="text-sm text-white/80 mt-1">
              {stat.label}
            </div>
            
            <div className="absolute -bottom-2 left-1/2 w-0 h-0.5 bg-[#FDE6C3] rounded-full transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%]" />
          </div>
        );
      })}
    </div>
  );
};

export default StatsSection;