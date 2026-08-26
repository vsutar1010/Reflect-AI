import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

const ProfileContext = createContext(null);

export function ProfileProvider({ children }) {
  const { user, authLoading } = useAuth();
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('reflect_active_profile');
      return saved ? JSON.parse(saved) : null;
    } catch (_) {
      return null;
    }
  });
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [error, setError] = useState(null);

  const fetchProfiles = useCallback(async () => {
    setLoadingProfiles(true);
    setError(null);
    try {
      const list = await api.getProfiles();
      setProfiles(list);
      
      // Sync selected profile if it exists in list
      if (selectedProfile) {
        const found = list.find((p) => p.id === selectedProfile.id);
        if (found) {
          setSelectedProfile(found);
          localStorage.setItem('reflect_active_profile', JSON.stringify(found));
        } else {
          setSelectedProfile(null);
          localStorage.removeItem('reflect_active_profile');
        }
      } else if (list.length > 0) {
        // Default to first profile if none selected
        setSelectedProfile(list[0]);
        localStorage.setItem('reflect_active_profile', JSON.stringify(list[0]));
      }
    } catch (err) {
      console.error('Failed to fetch profiles:', err);
      setError(err.message);
    } finally {
      setLoadingProfiles(false);
    }
  }, [selectedProfile]);

  useEffect(() => {
    if (authLoading) return;

    if (user) {
      fetchProfiles();
    } else {
      setProfiles([]);
      setSelectedProfile(null);
      localStorage.removeItem('reflect_active_profile');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, authLoading]);

  const selectProfile = (profile) => {
    setSelectedProfile(profile);
    if (profile) {
      localStorage.setItem('reflect_active_profile', JSON.stringify(profile));
    } else {
      localStorage.removeItem('reflect_active_profile');
    }
  };

  const removeProfile = async (id) => {
    try {
      await api.deleteProfile(id);
      if (selectedProfile && selectedProfile.id === id) {
        selectProfile(null);
      }
      await fetchProfiles();
    } catch (err) {
      console.error('Failed to delete profile:', err);
      throw err;
    }
  };

  return (
    <ProfileContext.Provider
      value={{
        profiles,
        selectedProfile,
        selectProfile,
        removeProfile,
        fetchProfiles,
        loadingProfiles,
        error,
      }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfile must be used within a ProfileProvider');
  }
  return context;
}
