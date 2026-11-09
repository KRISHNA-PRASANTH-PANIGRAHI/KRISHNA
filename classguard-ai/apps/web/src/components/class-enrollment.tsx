"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import type { ClassPlan, MemberRecord } from "@/lib/types";
import { useApp } from "./app-provider";
import { Icon } from "./icons";
import { requestMessage, useRequestLifetime } from "@/lib/request-scope";
import { memberLabel } from "./people";

export function ClassEnrollment({ classPlan }: { classPlan: ClassPlan }) {
  const app = useApp();
  const canManage =
    !app.preview &&
    app.session &&
    app.institution?.institution_id === classPlan.institution_id &&
    (app.institution.role === "admin" ||
      (app.institution.role === "teacher" &&
        classPlan.created_by === app.session.user.id));
  if (!canManage) return null;
  return (
    <EnrollmentManager
      key={`${app.session!.user.id}:${classPlan.institution_id}:${classPlan.id}`}
      classPlan={classPlan}
    />
  );
}

function EnrollmentManager({ classPlan }: { classPlan: ClassPlan }) {
  const app = useApp();
  const lifetime = useRequestLifetime();
  const token = app.session!.access_token;
  const base = `/v1/institutions/${encodeURIComponent(classPlan.institution_id)}`;
  const endpoint = `${base}/classes/${encodeURIComponent(classPlan.id)}/enrollments`;
  const [members, setMembers] = useState<MemberRecord[]>([]);
  const [enrolled, setEnrolled] = useState<MemberRecord[]>([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSelected("");
    Promise.all([
      apiRequest<{ items: MemberRecord[] }>(`${base}/members`, {
        token,
        signal: controller.signal,
      }),
      apiRequest<{ items: MemberRecord[] }>(endpoint, {
        token,
        signal: controller.signal,
      }),
    ])
      .then(([members, enrolled]) => {
        if (controller.signal.aborted) return;
        setMembers(
          members.items.filter(
            (member) => member.active && member.role === "student",
          ),
        );
        setEnrolled(enrolled.items);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setMembers([]);
          setEnrolled([]);
          setError(requestMessage(error, "Enrollment could not be loaded."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [base, endpoint, token, version]);

  async function changeEnrollment(userId: string, remove = false) {
    if (busy || !userId) return;
    const signal = lifetime.current?.signal;
    setBusy(userId);
    setError("");
    setNotice("");
    try {
      await apiRequest<MemberRecord | null>(
        remove ? `${endpoint}/${encodeURIComponent(userId)}` : endpoint,
        {
          method: remove ? "DELETE" : "POST",
          token,
          signal,
          ...(remove ? {} : { body: { user_id: userId } }),
        },
      );
      if (signal?.aborted) return;
      setNotice(
        remove
          ? "Student removed from this class."
          : "Student enrolled. This class is now on their timetable.",
      );
      setVersion((value) => value + 1);
    } catch (error) {
      if (!signal?.aborted)
        setError(requestMessage(error, "Enrollment could not be updated."));
    } finally {
      if (!signal?.aborted) setBusy("");
    }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void changeEnrollment(selected);
  }
  const available = members.filter(
    (member) => !enrolled.some((item) => item.user_id === member.user_id),
  );
  return (
    <section className="enrollment-panel" aria-labelledby="enrollment-heading">
      <div className="section-heading">
        <h3 id="enrollment-heading">Class enrollment</h3>
        <span className="count-pill">{enrolled.length}</span>
      </div>
      <p className="fine-print">
        Enrolled students can see this class in their timetable.
      </p>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button onClick={() => setVersion((value) => value + 1)}>
            Retry
          </button>
        </div>
      )}
      {notice && (
        <div className="notice success" role="status">
          {notice}
        </div>
      )}
      {loading ? (
        <p className="muted" role="status">
          Loading enrollment…
        </p>
      ) : (
        <>
          {enrolled.length ? (
            <ul className="member-list">
              {enrolled.map((member) => (
                <li className="member-row" key={member.user_id}>
                  <span className="member-avatar">
                    {(member.email || "U")[0].toUpperCase()}
                  </span>
                  <div className="member-identity">
                    <b title={member.email || member.user_id}>
                      {memberLabel(member)}
                    </b>
                    <span>
                      {member.active
                        ? "Enrolled student"
                        : "Institution access removed"}
                    </span>
                  </div>
                  <button
                    className="button subtle small"
                    onClick={() => changeEnrollment(member.user_id, true)}
                    disabled={Boolean(busy)}
                    aria-label={`Remove ${memberLabel(member)} from class`}
                  >
                    {busy === member.user_id ? "Saving…" : "Remove"}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="enrollment-empty">No students enrolled yet.</p>
          )}
          <form className="form-stack enrollment-form" onSubmit={submit}>
            <label>
              Add a student
              <select
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
                disabled={Boolean(busy) || !available.length}
                required
              >
                <option value="">
                  {available.length
                    ? "Choose a student"
                    : "No other students available"}
                </option>
                {available.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {memberLabel(member)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="button secondary"
              disabled={Boolean(busy) || !selected}
            >
              <Icon name="plus" size={16} />
              {busy === selected && selected ? "Enrolling…" : "Add student"}
            </button>
          </form>
          {!available.length && (
            <p className="fine-print">
              Your administrator can invite more students from People. They
              appear here after accepting their invitation.
            </p>
          )}
        </>
      )}
    </section>
  );
}
