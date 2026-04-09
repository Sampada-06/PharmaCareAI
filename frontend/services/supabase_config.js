// Supabase configuration for Vanilla JS
// Using Supabase CDN: https://cdn.jsdelivr.net/npm/@supabase/supabase-js

const SUPABASE_URL = 'https://knnbheuerdsjbbgxdoay.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtubmJoZXVlcmRzamJiZ3hkb2F5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwNDA0MTMsImV4cCI6MjA4NzYxNjQxM30.k3MlhUj7qOhBCHPJ3NRTvKgA965Fbn7GzTnUPEwaU7c';

// Initialize Supabase client
// For browser environments using CDN, we use supabase.createClient
const { createClient } = window.supabase;
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
