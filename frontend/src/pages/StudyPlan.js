import React, { useEffect, useState } from 'react';
import {
  getRoadmap,
  generateRoadmap,
  completeRoadmapDay,
} from '../services/studentService';

function StudyPlan() {
  const [roadmap, setRoadmap] = useState({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const loadRoadmap = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await getRoadmap();

      console.log('Roadmap response:', data);

      setRoadmap(data.roadmap || {});
    } catch (err) {
      console.error('Failed to load roadmap:', err);
      setError(
        err.response?.data?.error ||
        'Failed to load your learning roadmap.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoadmap();
  }, []);

  const handleGenerateRoadmap = async () => {
    try {
      setGenerating(true);
      setError('');

      const data = await generateRoadmap();

      console.log('Generated roadmap:', data);

      setRoadmap(data.roadmap || {});
    } catch (err) {
      console.error('Failed to generate roadmap:', err);
      setError(
        err.response?.data?.error ||
        'Failed to generate your roadmap.'
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleComplete = async (planId) => {
    try {
      await completeRoadmapDay(planId);

      // Reload the roadmap so the completed state
      // comes directly from the backend.
      await loadRoadmap();
    } catch (err) {
      console.error('Failed to complete roadmap day:', err);
      setError(
        err.response?.data?.error ||
        'Failed to mark this day as completed.'
      );
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <h1 style={styles.title}>Learning Roadmap</h1>
        <p style={styles.message}>Loading your roadmap...</p>
      </div>
    );
  }

  const skills = Object.keys(roadmap);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Learning Roadmap</h1>
          <p style={styles.subtitle}>
            Follow your personalized learning path and build the skills
            you need for your target career.
          </p>
        </div>

        <button
          onClick={handleGenerateRoadmap}
          disabled={generating}
          style={styles.generateButton}
        >
          {generating ? 'Generating...' : 'Generate Roadmap'}
        </button>
      </div>

      {error && (
        <div style={styles.error}>
          {error}
        </div>
      )}

      {skills.length === 0 ? (
        <div style={styles.empty}>
          <h2>No roadmap yet</h2>
          <p>
            Generate your personalized roadmap based on your current
            skill gaps.
          </p>

          <button
            onClick={handleGenerateRoadmap}
            disabled={generating}
            style={styles.generateButton}
          >
            {generating ? 'Generating...' : 'Generate My Roadmap'}
          </button>
        </div>
      ) : (
        <div>
          {skills.map((skillName) => {
            const days = roadmap[skillName] || [];

            return (
              <section key={skillName} style={styles.skillSection}>
                <h2 style={styles.skillTitle}>
                  {skillName}
                </h2>

                <div style={styles.timeline}>
                  {days.map((day) => (
                    <div key={day.id} style={styles.card}>
                      <div style={styles.dayNumber}>
                        Day {day.day_number}
                      </div>

                      <div style={styles.cardContent}>
                        <h3 style={styles.topic}>
                          {day.topic}
                        </h3>

                        <p style={styles.description}>
                          {day.description}
                        </p>

                        <div style={styles.infoRow}>
                          <span>
                            ⏱ {day.duration_hours} hours
                          </span>

                          {day.resource_link && (
                            <span>
                              📚 {day.resource_link}
                            </span>
                          )}
                        </div>

                        {day.is_completed ? (
                          <div style={styles.completed}>
                            ✓ Completed
                          </div>
                        ) : (
                          <button
                            onClick={() => handleComplete(day.id)}
                            style={styles.completeButton}
                          >
                            Mark Complete
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    padding: '40px',
    background: '#0f172a',
    color: '#e2e8f0',
    fontFamily: 'Inter, sans-serif',
  },

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '20px',
    marginBottom: '40px',
    flexWrap: 'wrap',
  },

  title: {
    margin: 0,
    fontSize: '36px',
    fontWeight: 700,
    fontFamily: 'Space Grotesk, sans-serif',
  },

  subtitle: {
    marginTop: '10px',
    color: '#94a3b8',
    maxWidth: '700px',
    lineHeight: 1.6,
  },

  generateButton: {
    border: 'none',
    borderRadius: '10px',
    padding: '12px 20px',
    background: '#14b8a6',
    color: '#ffffff',
    fontWeight: 600,
    cursor: 'pointer',
  },

  message: {
    color: '#94a3b8',
  },

  error: {
    padding: '14px 18px',
    marginBottom: '25px',
    borderRadius: '10px',
    background: '#451a1a',
    color: '#fca5a5',
  },

  empty: {
    padding: '40px',
    textAlign: 'center',
    borderRadius: '16px',
    background: '#1e293b',
  },

  skillSection: {
    marginBottom: '45px',
  },

  skillTitle: {
    fontSize: '26px',
    marginBottom: '20px',
    color: '#5eead4',
    fontFamily: 'Space Grotesk, sans-serif',
  },

  timeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },

  card: {
    display: 'flex',
    gap: '20px',
    padding: '22px',
    borderRadius: '16px',
    background: '#1e293b',
    border: '1px solid #334155',
  },

  dayNumber: {
    minWidth: '70px',
    color: '#5eead4',
    fontWeight: 700,
  },

  cardContent: {
    flex: 1,
  },

  topic: {
    margin: '0 0 10px',
    fontSize: '20px',
    fontFamily: 'Space Grotesk, sans-serif',
  },

  description: {
    margin: '0 0 15px',
    color: '#cbd5e1',
    lineHeight: 1.6,
  },

  infoRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '20px',
    color: '#94a3b8',
    fontSize: '14px',
    marginBottom: '18px',
  },

  completeButton: {
    border: '1px solid #14b8a6',
    borderRadius: '8px',
    padding: '9px 15px',
    background: 'transparent',
    color: '#5eead4',
    fontWeight: 600,
    cursor: 'pointer',
  },

  completed: {
    display: 'inline-block',
    padding: '8px 14px',
    borderRadius: '8px',
    background: '#134e4a',
    color: '#5eead4',
    fontWeight: 600,
  },
};

export default StudyPlan;