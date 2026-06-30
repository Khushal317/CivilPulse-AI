import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { z } from "zod";

import { ApiError } from "../../api/client";
import { Seo } from "../../components/Seo";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { CategoryBadge, SeverityBadge, StatusBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { Dialog } from "../../components/ui/Dialog";
import { SelectField, TextAreaField, TextField } from "../../components/ui/FormField";
import { GeminiLabel } from "../../components/ui/GeminiLabel";
import { useNotifications } from "../../app/notificationContext";
import {
  cancelReport,
  getReportDraft,
  publishReport,
  reportImageUrl,
  updateReportDraft,
} from "./api";
import { categoryOptions, severityOptions, urgencyOptions } from "./constants";
import { reviewSchema } from "./reviewSchema";
import type { PublishedReport, ReportDraftUpdate } from "./types";

type ReviewValues = z.infer<typeof reviewSchema>;

function draftValues(draft: Awaited<ReturnType<typeof getReportDraft>>): ReviewValues {
  return {
    title: draft.title,
    original_description: draft.original_description,
    ai_summary: draft.ai_summary,
    category: draft.category,
    severity: draft.severity,
    urgency_level: draft.urgency_level,
    urgency_reason: draft.urgency_reason,
    suggested_department: draft.suggested_department,
    safety_risk: draft.safety_risk,
    citizen_explanation: draft.citizen_explanation,
    suggested_next_action: draft.suggested_next_action,
    location: draft.location,
    landmark: draft.landmark ?? "",
  };
}

function isGeminiModel(model: string) {
  return model.toLowerCase().includes("gemini");
}

export function ReportReviewPage() {
  const { draftId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [editing, setEditing] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [published, setPublished] = useState<PublishedReport | null>(null);
  const draftQuery = useQuery({
    enabled: Boolean(draftId),
    queryKey: ["report-draft", draftId],
    queryFn: ({ signal }) => getReportDraft(draftId!, signal),
    retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 1,
  });
  const {
    formState: { errors, isDirty },
    handleSubmit,
    register,
    reset,
  } = useForm<ReviewValues>({
    resolver: zodResolver(reviewSchema),
  });

  useEffect(() => {
    if (draftQuery.data) reset(draftValues(draftQuery.data));
  }, [draftQuery.data, reset]);

  const save = useMutation({
    mutationFn: (values: ReviewValues) =>
      updateReportDraft(draftId!, {
        ...values,
        landmark: values.landmark || null,
      }),
    onSuccess: (draft) => {
      queryClient.setQueryData(["report-draft", draftId], draft);
      reset(draftValues(draft));
      setEditing(false);
      notify({
        message: "Your edits are saved to this private draft.",
        title: "Draft updated",
        tone: "success",
      });
    },
  });
  const publish = useMutation({
    mutationFn: async (values: ReviewValues) => {
      const changes: ReportDraftUpdate = {
        ...values,
        landmark: values.landmark || null,
      };
      if (isDirty) await updateReportDraft(draftId!, changes);
      return publishReport(draftId!);
    },
    onSuccess: setPublished,
  });
  const cancel = useMutation({
    mutationFn: () => cancelReport(draftId!),
    onSuccess: () => {
      void navigate("/report", { replace: true });
    },
  });

  if (!draftId) {
    return (
      <section className="page-section">
        <Seo title="Review unavailable" />
        <div className="container narrow">
          <ErrorState title="The report draft link is incomplete" />
        </div>
      </section>
    );
  }

  if (draftQuery.isPending) {
    return (
      <section className="page-section">
        <Seo title="Review report" />
        <div className="container narrow">
          <Spinner label="Loading AI review…" />
        </div>
      </section>
    );
  }

  if (draftQuery.isError) {
    const expired = draftQuery.error instanceof ApiError && draftQuery.error.code === "draft_expired";
    return (
      <section className="page-section">
        <Seo title={expired ? "Draft expired" : "Review unavailable"} />
        <div className="container narrow">
          <ErrorState
            description={
              expired
                ? "Drafts expire to protect temporary uploads. Analyze the report again."
                : draftQuery.error.message
            }
            title={expired ? "This report draft has expired" : "The report draft is unavailable"}
          />
          <div className="state-followup">
            <Link className={buttonClassName("primary")} to="/report">
              Start a new report
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const draft = draftQuery.data;
  if (published) {
    return (
      <section className="page-section publication-success">
        <Seo
          description="Your CivicPulse AI report has been published to the public tracker."
          title="Report published"
        />
        <div className="container narrow">
          <Card padding="large">
            <span className="success-mark" aria-hidden="true">
              ✓
            </span>
            <p className="eyebrow">Report published</p>
            <h1>Your issue is now trackable.</h1>
            <p className="page-copy">
              Public reference <strong>{published.public_reference}</strong> has been created with
              Reported status. It can now collect community verification and contribute to local
              Civic Genome signals.
            </p>
            <div className="review-badges">
              <StatusBadge status={published.status} />
            </div>
            <div className="actions">
              <Link className={buttonClassName("primary")} to="/issues">
                View public tracker
              </Link>
              <Link className={buttonClassName("secondary")} to="/report">
                Report another issue
              </Link>
            </div>
          </Card>
        </div>
      </section>
    );
  }

  const requestError = save.error ?? publish.error ?? cancel.error;
  const generatedByGemini = isGeminiModel(draft.ai_model);

  return (
    <section className="page-section review-page">
      <Seo
        description="Review and edit the AI-structured civic issue before publishing it to the public tracker."
        title="Review report"
      />
      <div className="container review-layout">
        <div className="review-heading">
          <div>
            <div className="review-heading-labels">
              <p className="eyebrow">AI review</p>
              <GeminiLabel>
                {generatedByGemini ? "Generated by Gemini" : "AI-assisted draft"}
              </GeminiLabel>
            </div>
            <h1>Review before publishing</h1>
            <p className="page-copy">
              CivicPulse AI organized this into a civic report draft. You stay in control: correct
              anything unclear before making the issue public.
            </p>
          </div>
          <div className="review-badges">
            <CategoryBadge category={draft.category} />
            <SeverityBadge severity={draft.severity} />
          </div>
        </div>

        <div className="review-grid">
          <Card className="review-image-card" padding="none">
            <img alt="Citizen-submitted civic issue" src={reportImageUrl(draft.image_url)} />
            <div>
              <strong>{draft.location}</strong>
              <span>{draft.landmark || "No landmark provided"}</span>
              <small>Original citizen evidence</small>
            </div>
          </Card>

          <form
            className="review-form"
            onSubmit={(event) => {
              void handleSubmit((values) => save.mutate(values))(event);
            }}
          >
            <Card padding="large">
              <div className="review-card-heading">
                <div>
                  <div className="review-card-kicker">
                    <p className="eyebrow">Structured complaint</p>
                    <GeminiLabel>
                      {generatedByGemini ? "Gemini structured" : "AI structured"}
                    </GeminiLabel>
                  </div>
                  <h2>Public report details</h2>
                </div>
                {!editing && (
                  <Button onClick={() => setEditing(true)} size="small" variant="secondary">
                    Edit details
                  </Button>
                )}
              </div>

              {editing ? (
                <div className="form-stack">
                  <TextField error={errors.title?.message} label="Issue title" {...register("title")} />
                  <TextAreaField
                    error={errors.original_description?.message}
                    label="Original description"
                    rows={4}
                    {...register("original_description")}
                  />
                  <TextAreaField
                    error={errors.ai_summary?.message}
                    label="Official complaint summary"
                    rows={5}
                    {...register("ai_summary")}
                  />
                  <div className="form-grid">
                    <SelectField label="Category" {...register("category")}>
                      {categoryOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </SelectField>
                    <SelectField label="Severity" {...register("severity")}>
                      {severityOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </SelectField>
                  </div>
                  <div className="form-grid">
                    <TextField label="Location" {...register("location")} />
                    <TextField label="Landmark" optional {...register("landmark")} />
                  </div>
                  <SelectField label="Urgency" {...register("urgency_level")}>
                    {urgencyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </SelectField>
                  <TextAreaField label="Urgency reason" rows={3} {...register("urgency_reason")} />
                  <TextField label="Suggested department" {...register("suggested_department")} />
                  <TextAreaField label="Safety risk" rows={3} {...register("safety_risk")} />
                  <TextAreaField
                    label="Citizen-friendly explanation"
                    rows={3}
                    {...register("citizen_explanation")}
                  />
                  <TextAreaField
                    label="Suggested next action"
                    rows={3}
                    {...register("suggested_next_action")}
                  />
                  <div className="dialog-actions">
                    <Button
                      onClick={() => {
                        reset(draftValues(draft));
                        setEditing(false);
                      }}
                      variant="secondary"
                    >
                      Discard edits
                    </Button>
                    <Button isLoading={save.isPending} type="submit">
                      Save changes
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="review-summary">
                  <div className="review-control-note">
                    <strong>Human review required.</strong>
                    <span>
                      This draft is private until you submit it. Edit anything that feels wrong.
                    </span>
                  </div>
                  <h3>{draft.title}</h3>
                  <p>{draft.ai_summary}</p>
                  <dl className="review-details">
                    <div>
                      <dt>Suggested department</dt>
                      <dd>{draft.suggested_department}</dd>
                    </div>
                    <div>
                      <dt>Urgency</dt>
                      <dd>{draft.urgency_level}</dd>
                    </div>
                    <div>
                      <dt>Urgency reason</dt>
                      <dd>{draft.urgency_reason}</dd>
                    </div>
                    <div>
                      <dt>Safety risk</dt>
                      <dd>{draft.safety_risk}</dd>
                    </div>
                    <div>
                      <dt>Suggested next action</dt>
                      <dd>{draft.suggested_next_action}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </Card>

            {requestError && (
              <ErrorState
                description={
                  requestError instanceof Error
                    ? requestError.message
                    : "The draft action could not be completed."
                }
                title="The draft could not be updated"
              />
            )}

            <div className="form-submit-bar">
              <Button onClick={() => setCancelOpen(true)} variant="ghost">
                Cancel report
              </Button>
              <div className="review-submit-actions">
                <span>Draft expires {new Date(draft.expires_at).toLocaleString()}</span>
                <Button
                  isLoading={publish.isPending}
                  onClick={() => void handleSubmit((values) => publish.mutate(values))()}
                >
                  Submit report
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <Dialog
        confirmLabel="Cancel report"
        isOpen={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => cancel.mutate()}
        title="Delete this private draft?"
        variant="danger"
      >
        The temporary image and AI analysis will be removed. This cannot be undone.
      </Dialog>
    </section>
  );
}
