import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { TbRoute, TbCheck } from 'react-icons/tb';
import skillService from '../services/skillService';
import { apiErrorMessage } from '../utils/apiErrors';

/**
 * "Add to roadmap" for one missing skill. The server refuses duplicates (any case
 * or spelling variant already planned) and skills that are already verified, so
 * clicking twice can never create two entries.
 */
export default function AddToRoadmapButton({ skill, jobId, initiallyPlanned = false }) {
  const [state, setState] = useState(initiallyPlanned ? 'planned' : 'idle'); // idle | busy | planned | verified | error
  const [message, setMessage] = useState('');

  useEffect(() => {
    setState(initiallyPlanned ? 'planned' : 'idle');
    setMessage('');
  }, [skill, jobId, initiallyPlanned]);

  const add = async () => {
    setState('busy');
    try {
      const r = await skillService.addSkillToRoadmap(skill, jobId);
      setMessage(r.message || '');
      setState(r.verified ? 'verified' : 'planned');
    } catch (e) {
      setMessage(apiErrorMessage(e, 'Could not add this skill to your roadmap.'));
      setState('error');
    }
  };

  if (state === 'planned') {
    return (
      <Link to="/roadmap" className="text-emerald-300 hover:text-emerald-200 flex items-center gap-1" title={message || undefined}>
        <TbCheck className="w-3 h-3" /> On your roadmap
      </Link>
    );
  }
  if (state === 'verified') {
    return <span className="text-emerald-300" title={message}>Already verified</span>;
  }
  return (
    <span className="flex items-center gap-1.5">
      <button type="button" onClick={add} disabled={state === 'busy'}
        className="text-accent-300 hover:text-accent-200 flex items-center gap-1 disabled:opacity-50">
        <TbRoute className="w-3 h-3" /> {state === 'busy' ? 'Adding…' : 'Add to roadmap'}
      </button>
      {state === 'error' && <span className="text-rose-300">{message}</span>}
    </span>
  );
}
