// src/pages/Login.jsx
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast, { Toaster } from 'react-hot-toast';
import * as api from '../services/api';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error('لطفاً همه فیلدها را پر کنید');
      return;
    }
    try {
      await api.login({ username, password });
      toast.success('ورود با موفقیت انجام شد!');
      setTimeout(() => navigate('/dashboard'), 1200);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <motion.div 
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '-100%' }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="min-h-screen relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #1A4F54 0%, #6BA5AA 39%, #C8E8EB 100%)'
      }}
    >
      <Toaster position="top-center" />
      
      {/* دایره بالای سمت راست */}
      <motion.div 
        className="absolute top-32 right-20 w-32 h-32 rounded-full border-2 border-[#FAEEDB]/25"
        animate={{ y: [0, -25, 0], x: [0, 15, 0] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
      />
      
      {/* دایره پایین سمت چپ */}
      <motion.div 
        className="absolute top-96 left-20 w-40 h-40 rounded-full border-2 border-[#FAEEDB]/20"
        animate={{ y: [0, 20, 0], x: [0, -10, 0] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      />
      
      {/* دایره‌های کوچک محو */}
      <div className="absolute top-20 left-10 w-24 h-24 rounded-full border border-[#FAEEDB]/15 animate-pulse"></div>
      <div className="absolute bottom-20 right-10 w-32 h-32 rounded-full border border-[#FAEEDB]/10 animate-pulse delay-700"></div>
      
      {/* هدر شیشه‌ای */}
      <header className="fixed top-6 left-6 right-6 z-50">
        <div className="bg-[#FAEEDB]/24 backdrop-blur-md rounded-full px-5 py-2 flex items-center justify-between shadow-lg border border-white/20">
          <button 
            onClick={() => navigate(-1)}
            className="w-8 h-8 rounded-full bg-[#FAEEDB] flex items-center justify-center hover:scale-105 transition-transform duration-200 shadow-md"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="#094B50" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="text-right">
            <h1 className="text-xl font-bold text-[#FAEEDB] tracking-tight">پلی‌لایف</h1>
          </div>
        </div>
      </header>

      {/* فاصله از بالا */}
      <div className="h-36"></div>

      {/* دایره‌های روی هم با فاصله بیشتر */}
      <div className="relative flex justify-center items-center h-40 -mb-16 z-0">
        <motion.div 
          className="absolute w-32 h-32 rounded-full border-2 border-[#FAEEDB]/20"
          animate={{ y: [0, -10, 0], x: [0, 8, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          style={{ left: '50%', top: '60%', transform: 'translate(-50%, -50%)' }}
        />
        <motion.div 
          className="absolute w-24 h-24 rounded-full border-2 border-[#FAEEDB]/30"
          animate={{ y: [0, 8, 0], x: [0, -6, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
          style={{ left: '35%', top: '35%', transform: 'translate(-50%, -50%)' }}
        />
        <motion.div 
          className="absolute w-20 h-20 rounded-full border-2 border-[#FAEEDB]/40"
          animate={{ y: [0, -6, 0], x: [0, 8, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
          style={{ left: '70%', top: '30%', transform: 'translate(-50%, -50%)' }}
        />
      </div>

      {/* POLYLIFE فانتزی */}
      <div className="text-center group relative z-10">
        <h2 
          className="text-7xl md:text-8xl lg:text-9xl font-extrabold tracking-wider transition-all duration-500 cursor-default inline-block"
          style={{ 
            fontFamily: "'Poppins', 'Vazirmatn', 'sans-serif'",
            background: 'linear-gradient(135deg, #FAEEDB 0%, #FFFFFF 50%, #FAEEDB 100%)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            textShadow: '0 5px 15px rgba(0,0,0,0.2)',
            letterSpacing: '0.1em'
          }}
        >
          POLYLIFE
        </h2>
        <div className="w-0 h-0.5 bg-gradient-to-r from-transparent via-[#FAEEDB] to-transparent mx-auto mt-4 group-hover:w-3/4 transition-all duration-700"></div>
      </div>

      {/* فاصله از پایین */}
      <div className="h-20"></div>

      {/* فرم ورود */}
      <div className="max-w-2xl mx-auto px-4">
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="bg-[#FAEEDB]/90 py-10 px-8 shadow-inner rounded-3xl"
        >
          <div className="max-w-md mx-auto text-center">
            
            <h2 className="text-4xl md:text-5xl font-extrabold text-[#094B50] mb-4">ورود</h2>
            <p className="text-[#094B50] text-base font-semibold mb-8">به خانواده پلی‌لایف خوش آمدید</p>
            
                        <form onSubmit={handleSubmit} className="space-y-5 text-right">
              
              {/* فیلد نام کاربری */}
              <div className="relative group">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-[#145156]/50 border-2 border-[#094B50] text-[#094B50] placeholder-[#094B50]/40 focus:outline-none focus:border-[#FDE6C3] transition pr-12"
                  placeholder="نام کاربری"
                  style={{ textAlign: 'right' }}
                  required
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 group-focus-within:text-[#FDE6C3] transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[#094B50]/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                  </svg>
                </div>
              </div>
              
              {/* فیلد رمز عبور */}
              <div className="relative group">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-[#145156]/50 border-2 border-[#094B50] text-[#094B50] placeholder-[#094B50]/40 focus:outline-none focus:border-[#FDE6C3] transition pr-12 pl-12"
                  placeholder="رمز عبور"
                  style={{ textAlign: 'right' }}
                  required
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 group-focus-within:text-[#FDE6C3] transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[#094B50]/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                  </svg>
                </div>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[#094B50]/40 hover:text-[#094B50] transition" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    {showPassword ? (
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    )}
                  </svg>
                </button>
              </div>
              
              {/* فراموشی رمز - سمت راست */}
              <div className="text-right">
                <Link to="/forgot-password" className="text-[#094B50]/70 text-sm hover:text-[#094B50] transition">
                  رمز عبور خود را فراموش کردید؟
                </Link>
              </div>
              
              {/* دکمه ورود */}
              <button
                type="submit"
                className="w-full bg-[#185E64] text-white py-3 rounded-xl font-bold hover:bg-[#0D3D42] transition duration-300 mt-2"
              >
                ورود
              </button>
              
              {/* به خاطر سپردن */}
              <div className="flex justify-end mt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-[#094B50]/80 text-sm">به خاطر سپردن</span>
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-2 border-[#094B50] bg-transparent checked:bg-[#094B50] focus:ring-0 focus:ring-offset-0"
                  />
                </label>
              </div>
            </form>
                        
            <div className="mt-6 mb-4">
              <div className="relative flex items-center justify-center">
                <div className="border-t border-[#094B50]/20 w-full"></div>
                <span className="px-4 text-[#094B50]/60 text-sm bg-[#FAEEDB]/90 absolute">یا ورود با</span>
              </div>
              
              <div className="flex items-center justify-center gap-6 mt-6">
                <button className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center hover:scale-110 transition">
                  <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.71 19.5C17.88 20.74 17 21.95 15.66 21.97C14.32 22 13.89 21.18 12.37 21.18C10.85 21.18 10.37 21.95 9.17 22C7.93 22.05 7.03 20.85 6.18 19.62C4.49 16.96 3.21 12.02 5.01 8.66C5.89 7.01 7.56 5.97 9.36 5.94C10.66 5.92 11.89 6.8 12.68 6.8C13.46 6.8 14.95 5.76 16.48 5.92C17.21 5.98 19.09 6.27 20.2 8.04C20.12 8.09 17.73 9.46 17.77 12.25C17.81 14.56 19.7 15.78 19.75 15.81C19.73 15.85 19.01 17.94 18.71 19.5Z" />
                  </svg>
                </button>
                <button className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center hover:scale-110 transition">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                  </svg>
                </button>
                <button className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center hover:scale-110 transition">
                  <svg className="w-5 h-5 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c5.05-.5 9-4.76 9-9.95z" />
                  </svg>
                </button>
              </div>
            </div>
            
            <p className="text-center text-[#094B50]/60 text-sm mt-4">
              حساب کاربری ندارید؟{' '}
              <Link to="/register" className="text-[#094B50] hover:underline font-medium">
                ثبت‌نام کنید
              </Link>
            </p>
          </div>
        </motion.div>
      </div>

      {/* بخش مزایا (4 کارت) */}
      <div className="max-w-4xl mx-auto px-4 py-16 relative">
        
        {/* دایره سمت راست */}
        <motion.div 
          className="absolute -right-20 top-1/3 w-40 h-40 rounded-full border-2 border-[#FAEEDB]/15"
          animate={{ y: [0, 15, 0], x: [0, -5, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        
        {/* دایره سمت چپ 1 */}
        <motion.div 
          className="absolute -left-20 top-10 w-32 h-32 rounded-full border-2 border-[#FAEEDB]/20"
          animate={{ y: [0, -10, 0], x: [0, 5, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        />
        
        {/* دایره سمت چپ 2 */}
        <motion.div 
          className="absolute -left-16 bottom-20 w-56 h-56 rounded-full border-2 border-[#FAEEDB]/10"
          animate={{ y: [0, 20, 0], x: [0, -8, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        />

        {/* دایره بالای سمت راست */}
        <motion.div 
          className="absolute -right-24 top-[10%] w-48 h-48 rounded-full border-2 border-[#FAEEDB]/12"
          animate={{ y: [0, -20, 0], x: [0, 10, 0] }}
          transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        />
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            { icon: "🥗", title: "PolyDiet", desc: "برنامه غذایی شخصی و کالری شمار" },
            { icon: "💪", title: "PolyWorkout", desc: "تمرینات هوشمند اختصاصی" },
            { icon: "📈", title: "PolyAnalysis", desc: "آنالیز هوشمند بدن و پیشرفت" },
            { icon: "👥", title: "PolySocial", desc: "جامعه ورزشی فعال و حامی" }
          ].map((feature, idx) => (
            <motion.div 
              key={idx}
              className="bg-white/10 backdrop-blur-md rounded-2xl p-5 border border-white/20 cursor-pointer relative overflow-hidden"
              whileHover={{ y: -8, scale: 1.03 }}
              transition={{ duration: 0.2 }}
            >
              <div className="absolute -top-5 -right-5 w-16 h-16 rounded-full bg-[#FAEEDB]/5 blur-xl"></div>
              <div className="flex items-center gap-4">
                <div className="text-4xl">{feature.icon}</div>
                <div className="text-right">
                  <h4 className="text-[#FAEEDB] font-bold text-lg">{feature.title}</h4>
                  <p className="text-[#FAEEDB]/70 text-sm">{feature.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
      
    </motion.div>
  );
}