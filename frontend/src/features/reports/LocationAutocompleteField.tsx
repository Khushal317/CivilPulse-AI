import {
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type FocusEvent,
  type Ref,
} from "react";

import { env } from "../../config/env";
import {
  GoogleMapsConfigurationError,
  loadGoogleMaps,
  type GoogleMapsGlobal,
} from "../../lib/maps/googleMapsLoader";
import { classNames } from "../../utils/classNames";

interface GoogleMapsListener {
  remove: () => void;
}

interface GoogleMapsPlaceResult {
  formatted_address?: string;
  geometry?: {
    location?: {
      lat: () => number;
      lng: () => number;
    };
  };
  name?: string;
}

interface GoogleMapsAutocomplete {
  addListener: (eventName: "place_changed", callback: () => void) => GoogleMapsListener;
  getPlace: () => GoogleMapsPlaceResult;
}

interface GoogleMapsWithAutocomplete extends GoogleMapsGlobal {
  maps: GoogleMapsGlobal["maps"] & {
    places: {
      Autocomplete: new (
        input: HTMLInputElement,
        options: {
          fields: string[];
          types: string[];
        },
      ) => GoogleMapsAutocomplete;
    };
  };
}

interface SelectedPlace {
  address: string;
  latitude: number;
  longitude: number;
}

interface LocationAutocompleteFieldProps {
  error?: string;
  inputRef?: Ref<HTMLInputElement>;
  name: string;
  onBlur: (event: FocusEvent<HTMLInputElement>) => void;
  onChange: (value: string) => void;
  onCoordinatesClear: () => void;
  onPlaceSelect: (place: SelectedPlace) => void;
  value: string;
}

type AutocompleteStatus = "fallback" | "loading" | "ready" | "unavailable";

const isGoogleMapsWithAutocomplete = (
  google: GoogleMapsGlobal,
): google is GoogleMapsWithAutocomplete =>
  typeof google.maps.places === "object" &&
  google.maps.places !== null &&
  "Autocomplete" in google.maps.places;

const assignRef = (ref: Ref<HTMLInputElement> | undefined, value: HTMLInputElement | null) => {
  if (typeof ref === "function") {
    ref(value);
    return;
  }

  if (ref) {
    ref.current = value;
  }
};

export function LocationAutocompleteField({
  error,
  inputRef,
  name,
  onBlur,
  onChange,
  onCoordinatesClear,
  onPlaceSelect,
  value,
}: LocationAutocompleteFieldProps) {
  const generatedId = useId();
  const inputElement = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<AutocompleteStatus>(
    env.isGoogleMapsConfigured ? "loading" : "fallback",
  );
  const messageId = `${generatedId}-message`;
  const hint =
    status === "ready"
      ? "Start typing and choose a Google suggestion when possible."
      : status === "loading"
        ? "Loading address suggestions..."
        : status === "unavailable"
          ? "Google suggestions are unavailable right now. You can still type the location manually."
          : "Type the location manually. Google Places is not configured yet.";

  useEffect(() => {
    if (!env.isGoogleMapsConfigured) {
      setStatus("fallback");
      return;
    }

    let isActive = true;
    let listener: GoogleMapsListener | null = null;

    setStatus("loading");
    void loadGoogleMaps()
      .then((google) => {
        if (!isActive || inputElement.current === null) return;
        if (!isGoogleMapsWithAutocomplete(google)) {
          setStatus("unavailable");
          return;
        }

        const autocomplete = new google.maps.places.Autocomplete(inputElement.current, {
          fields: ["formatted_address", "geometry", "name"],
          types: ["establishment", "geocode"],
        });

        listener = autocomplete.addListener("place_changed", () => {
          const place = autocomplete.getPlace();
          const location = place.geometry?.location;
          const address = place.formatted_address ?? place.name ?? inputElement.current?.value;

          if (!address || !location) return;

          onPlaceSelect({
            address,
            latitude: location.lat(),
            longitude: location.lng(),
          });
        });
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        if (error instanceof GoogleMapsConfigurationError) {
          setStatus("fallback");
          return;
        }
        setStatus("unavailable");
      });

    return () => {
      isActive = false;
      listener?.remove();
    };
  }, [onPlaceSelect]);

  return (
    <div className={classNames("field", error && "field-invalid")}>
      <div className="field-label-row">
        <label htmlFor={generatedId}>Area or location</label>
      </div>
      <input
        aria-describedby={messageId}
        aria-invalid={Boolean(error)}
        autoComplete="off"
        className="field-control"
        id={generatedId}
        name={name}
        onBlur={onBlur}
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          onChange(event.target.value);
          onCoordinatesClear();
        }}
        placeholder="Sector 12 or City Public School"
        ref={(element) => {
          inputElement.current = element;
          assignRef(inputRef, element);
        }}
        type="text"
        value={value}
      />
      <p className={classNames("field-message", error && "field-error")} id={messageId}>
        {error ?? hint}
      </p>
    </div>
  );
}
