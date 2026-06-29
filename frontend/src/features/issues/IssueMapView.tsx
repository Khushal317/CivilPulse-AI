import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../components/ui/Card";
import {
  GoogleMapsConfigurationError,
  loadGoogleMaps,
  type GoogleMapsGlobal,
} from "../../lib/maps/googleMapsLoader";
import type { IssueSeverity, IssueStatus } from "../../types/domain";
import type { PublicIssueMapItem, PublicIssueMapResponse } from "./types";

const CITY_CENTER = { lat: 26.9124, lng: 75.7873 };
const DEFAULT_ZOOM = 12;

type MarkerColor = "green" | "neutral" | "red" | "yellow";

interface GoogleMapsPoint {
  lat: number;
  lng: number;
}

interface GoogleMapsMap {
  fitBounds: (bounds: GoogleMapsBounds) => void;
  setCenter: (point: GoogleMapsPoint) => void;
  setZoom: (zoom: number) => void;
}

type GoogleMapsLatLng = object;

interface GoogleMapsBounds {
  extend: (point: GoogleMapsPoint) => void;
}

interface GoogleMapsInfoWindow {
  close: () => void;
  open: (options: { anchor?: GoogleMapsMarker; map: GoogleMapsMap }) => void;
  setContent: (content: string) => void;
  setPosition: (position: GoogleMapsPoint | GoogleMapsLatLng) => void;
}

interface GoogleMapsMapPanes {
  overlayMouseTarget: HTMLElement;
}

interface GoogleMapsMapProjection {
  fromLatLngToDivPixel: (
    position: GoogleMapsLatLng | GoogleMapsPoint,
  ) => { x: number; y: number } | null;
}

interface GoogleMapsOverlayView {
  draw?(): void;
  getPanes: () => GoogleMapsMapPanes | null;
  getProjection: () => GoogleMapsMapProjection | null;
  onAdd?(): void;
  onRemove?(): void;
  setMap: (map: GoogleMapsMap | null) => void;
}

interface GoogleMapsMarker extends GoogleMapsOverlayView {
  addListener: (eventName: "click", callback: () => void) => GoogleMapsListener;
}

interface GoogleMapsListener {
  remove: () => void;
}

interface GoogleMapsForIssues extends GoogleMapsGlobal {
  maps: GoogleMapsGlobal["maps"] & {
    InfoWindow: new () => GoogleMapsInfoWindow;
    LatLng?: new (latitude: number, longitude: number) => GoogleMapsLatLng;
    LatLngBounds: new () => GoogleMapsBounds;
    Map: new (
      element: HTMLElement,
      options: {
        center: GoogleMapsPoint;
        clickableIcons: boolean;
        fullscreenControl: boolean;
        mapTypeControl: boolean;
        streetViewControl: boolean;
        zoom: number;
      },
    ) => GoogleMapsMap;
    Marker?: new (options: {
      icon: {
        path: string;
        fillColor: string;
        fillOpacity: number;
        scale: number;
        strokeColor: string;
        strokeWeight: number;
      };
      map: GoogleMapsMap;
      position: GoogleMapsPoint;
      title: string;
    }) => GoogleMapsMarker;
    OverlayView?: new () => GoogleMapsOverlayView;
  };
}

interface IssueMapViewProps {
  result: PublicIssueMapResponse;
}

const statusLabels: Record<IssueStatus, string> = {
  community_verified: "Community verified",
  duplicate: "Duplicate",
  escalated: "Escalated",
  in_progress: "In progress",
  rejected: "Rejected",
  reported: "Reported",
  resolved: "Resolved",
};

const severityLabels: Record<IssueSeverity, string> = {
  critical: "Critical",
  high: "High",
  low: "Low",
  medium: "Medium",
};

const markerColors: Record<MarkerColor, string> = {
  green: "#2f8f46",
  neutral: "#5c6f64",
  red: "#c43d35",
  yellow: "#d9950d",
};

const markerPath =
  "M12 2C8.1 2 5 5.1 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.9-3.1-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z";

const escapeHtml = (value: string): string =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const isGoogleMapsForIssues = (google: GoogleMapsGlobal): google is GoogleMapsForIssues =>
  typeof google.maps.Map === "function" &&
  typeof (google.maps as Record<string, unknown>).InfoWindow === "function" &&
  typeof (google.maps as Record<string, unknown>).LatLngBounds === "function" &&
  (typeof (google.maps as Record<string, unknown>).Marker === "function" ||
    (typeof (google.maps as Record<string, unknown>).OverlayView === "function" &&
      typeof (google.maps as Record<string, unknown>).LatLng === "function"));

function markerColor(issue: PublicIssueMapItem): MarkerColor {
  if (issue.status === "resolved") return "green";
  if (issue.severity === "critical" || issue.severity === "high") return "red";
  if (issue.severity === "medium") return "yellow";
  return "neutral";
}

function popupHtml(issue: PublicIssueMapItem): string {
  const locationLine = issue.neighborhood ?? issue.location;
  const landmark = issue.landmark ? ` · ${escapeHtml(issue.landmark)}` : "";

  return `
    <article class="issue-map-popup">
      <p class="issue-reference">${escapeHtml(issue.public_reference)}</p>
      <h3>${escapeHtml(issue.title)}</h3>
      <dl>
        <div><dt>Category</dt><dd>${escapeHtml(issue.category.replaceAll("_", " "))}</dd></div>
        <div><dt>Severity</dt><dd>${escapeHtml(severityLabels[issue.severity])}</dd></div>
        <div><dt>Status</dt><dd>${escapeHtml(statusLabels[issue.status])}</dd></div>
        <div><dt>Neighborhood</dt><dd>${escapeHtml(locationLine)}${landmark}</dd></div>
      </dl>
      <a class="button button-primary button-small" href="/issues/${encodeURIComponent(issue.id)}">
        View Issue
      </a>
    </article>
  `;
}

function createHtmlMarkerElement(issue: PublicIssueMapItem): HTMLButtonElement {
  const marker = document.createElement("button");
  marker.type = "button";
  marker.className = `tracker-map-html-marker tracker-map-html-marker-${markerColor(issue)}`;
  marker.setAttribute("aria-label", `Open ${issue.title}`);
  marker.title = issue.title;
  return marker;
}

function createHtmlMarker(
  google: GoogleMapsForIssues,
  issue: PublicIssueMapItem,
  map: GoogleMapsMap,
  onClick: (position: GoogleMapsPoint | GoogleMapsLatLng) => void,
): GoogleMapsOverlayView | null {
  if (typeof google.maps.OverlayView !== "function" || typeof google.maps.LatLng !== "function") {
    return null;
  }

  const OverlayView = google.maps.OverlayView;
  const position = new google.maps.LatLng(issue.latitude, issue.longitude);

  class IssueMarkerOverlay extends OverlayView {
    private element: HTMLButtonElement | null = null;

    onAdd() {
      const panes = this.getPanes();
      if (!panes) return;

      this.element = createHtmlMarkerElement(issue);
      this.element.addEventListener("click", this.openPopup);
      panes.overlayMouseTarget.append(this.element);
    }

    draw() {
      if (!this.element) return;
      const point = this.getProjection()?.fromLatLngToDivPixel(position);
      if (!point) return;

      this.element.style.transform = `translate(${point.x}px, ${point.y}px) translate(-50%, -100%)`;
    }

    onRemove() {
      this.element?.removeEventListener("click", this.openPopup);
      this.element?.remove();
      this.element = null;
    }

    private openPopup = () => {
      onClick(position);
    };
  }

  const marker = new IssueMarkerOverlay();
  marker.setMap(map);
  return marker;
}

function createLegacyMarker(
  google: GoogleMapsForIssues,
  issue: PublicIssueMapItem,
  map: GoogleMapsMap,
  onClick: (position: GoogleMapsPoint, marker: GoogleMapsMarker) => void,
): { listener: GoogleMapsListener; marker: GoogleMapsMarker } | null {
  if (typeof google.maps.Marker !== "function") return null;

  const position = { lat: issue.latitude, lng: issue.longitude };
  const marker = new google.maps.Marker({
    icon: {
      fillColor: markerColors[markerColor(issue)],
      fillOpacity: 1,
      path: markerPath,
      scale: 1.45,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
    map,
    position,
    title: issue.title,
  });
  const listener = marker.addListener("click", () => onClick(position, marker));
  return { listener, marker };
}

function IssueMapFallback({
  message,
  result,
}: {
  message: string;
  result: PublicIssueMapResponse;
}) {
  return (
    <Card className="tracker-map-fallback" padding="large">
      <div>
        <p className="eyebrow">Map View</p>
        <h2>Map markers are ready</h2>
        <p>{message}</p>
        {result.unmapped_items > 0 && (
          <span>
            {result.unmapped_items} issue{result.unmapped_items === 1 ? "" : "s"} hidden from
            map because coordinates are not available yet.
          </span>
        )}
      </div>
      <ul className="tracker-map-fallback-list">
        {result.items.map((issue) => (
          <li key={issue.id}>
            <span className={`tracker-map-dot tracker-map-dot-${markerColor(issue)}`} />
            <div>
              <Link to={`/issues/${issue.id}`}>{issue.title}</Link>
              <p>
                {severityLabels[issue.severity]} · {statusLabels[issue.status]} ·{" "}
                {issue.neighborhood ?? issue.location}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function IssueMapView({ result }: IssueMapViewProps) {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const markers = useRef<GoogleMapsOverlayView[]>([]);
  const listeners = useRef<GoogleMapsListener[]>([]);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const cleanupMarkers = () => {
      listeners.current.forEach((listener) => listener.remove());
      listeners.current = [];
      markers.current.forEach((marker) => marker.setMap(null));
      markers.current = [];
    };

    void loadGoogleMaps()
      .then((google) => {
        if (!isActive || mapElement.current === null) return;
        if (!isGoogleMapsForIssues(google)) {
          setFallbackMessage(
            "Google Maps loaded without the map features needed for markers. The issue list below still links to every mappable report.",
          );
          return;
        }

        setFallbackMessage(null);
        cleanupMarkers();

        const map = new google.maps.Map(mapElement.current, {
          center: CITY_CENTER,
          clickableIcons: false,
          fullscreenControl: true,
          mapTypeControl: false,
          streetViewControl: false,
          zoom: DEFAULT_ZOOM,
        });
        const bounds = new google.maps.LatLngBounds();
        const infoWindow = new google.maps.InfoWindow();

        result.items.forEach((issue) => {
          const position = { lat: issue.latitude, lng: issue.longitude };
          bounds.extend(position);

          const openPopup = (
            popupPosition: GoogleMapsPoint | GoogleMapsLatLng,
            marker?: GoogleMapsMarker,
          ) => {
            infoWindow.setContent(popupHtml(issue));
            if (marker) {
              infoWindow.open({ anchor: marker, map });
              return;
            }

            infoWindow.setPosition(popupPosition);
            infoWindow.open({ map });
          };

          const htmlMarker = createHtmlMarker(google, issue, map, openPopup);
          if (htmlMarker) {
            markers.current.push(htmlMarker);
            return;
          }

          const markerResult = createLegacyMarker(google, issue, map, openPopup);
          if (markerResult) {
            markers.current.push(markerResult.marker);
            listeners.current.push(markerResult.listener);
          }
        });

        if (result.items.length === 1) {
          map.setCenter({
            lat: result.items[0].latitude,
            lng: result.items[0].longitude,
          });
          map.setZoom(15);
        } else {
          map.fitBounds(bounds);
        }
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        setFallbackMessage(
          error instanceof GoogleMapsConfigurationError
            ? "Google Maps is not configured yet. Add a valid Maps JavaScript API key to show markers on the map."
            : "Google Maps could not be loaded. This is usually caused by billing, API activation, referrer restrictions, quota, or network access.",
        );
      });

    return () => {
      isActive = false;
      cleanupMarkers();
    };
  }, [result]);

  if (fallbackMessage) {
    return <IssueMapFallback message={fallbackMessage} result={result} />;
  }

  return (
    <Card className="tracker-map-card" padding="none">
      <div className="tracker-map-canvas" ref={mapElement} />
      <div className="tracker-map-footer">
        <div>
          <strong>{result.items.length} marker{result.items.length === 1 ? "" : "s"} shown</strong>
          {result.unmapped_items > 0 && (
            <span>
              {result.unmapped_items} issue{result.unmapped_items === 1 ? "" : "s"} hidden because
              coordinates are not available yet.
            </span>
          )}
        </div>
        <div className="tracker-map-legend" aria-label="Map marker legend">
          <span><i className="tracker-map-dot tracker-map-dot-red" />High</span>
          <span><i className="tracker-map-dot tracker-map-dot-yellow" />Medium</span>
          <span><i className="tracker-map-dot tracker-map-dot-green" />Resolved</span>
        </div>
      </div>
    </Card>
  );
}
