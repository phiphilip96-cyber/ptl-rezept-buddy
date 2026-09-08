import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import Login from "./pages/Login";
import Profil from "./pages/Profil";
import Chat from "./pages/Chat";
import Heute from "./pages/Heute";
import Ich, { CheckinSeite } from "./pages/Ich";
import { PlaeneListe, PlanDetail } from "./pages/Plaene";
import { CoachChat, CoachKunde, CoachKunden, CoachLogin, CoachRegeln } from "./pages/Coach";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/heute" replace />} />
        <Route path="/heute" element={<Heute />} />
        <Route path="/ich" element={<Ich />} />
        <Route path="/checkin" element={<CheckinSeite />} />
        <Route path="/login" element={<Login />} />
        <Route path="/profil" element={<Profil />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:id" element={<Chat />} />
        <Route path="/plaene" element={<PlaeneListe />} />
        <Route path="/plaene/:id" element={<PlanDetail />} />
        <Route path="/coach/login" element={<CoachLogin />} />
        <Route path="/coach" element={<CoachKunden />} />
        <Route path="/coach/kunden/:id" element={<CoachKunde />} />
        <Route path="/coach/chats/:id" element={<CoachChat />} />
        <Route path="/coach/regeln" element={<CoachRegeln />} />
        <Route path="*" element={<Navigate to="/heute" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
