// Path: /maya-transfer. Visibility: Protected.
// Requires MAYA_OWNER_CELL and MAYA_STUDIO_WEBHOOK_URL.
// Invoke through Studio's TwiML Redirect widget, not Run Function.
exports.handler = function (context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();

  try {
    const endpoint = new URL(
      `https://${context.DOMAIN_NAME}/maya-transfer`
    );

    const stepUrl = (step) => {
      const url = new URL(endpoint);
      url.searchParams.set("step", step);
      return url.toString();
    };

    switch (event.step || "start") {
      case "screen": {
        const gather = twiml.gather({
          input: "dtmf",
          numDigits: 1,
          timeout: 8,
          actionOnEmptyResult: true,
          action: stepUrl("accept"),
          method: "POST"
        });

        gather.say(
          "Cloud Systems Direct. Press 1 to accept this call."
        );
        break;
      }

      case "accept": {
        // Only pressing 1 allows the caller to connect.
        // Otherwise, end only the call to your cell.
        if (event.Digits !== "1") {
          twiml.hangup();
        }
        break;
      }

      case "result": {
        const connected =
          event.DialBridged === true ||
          event.DialBridged === "true";

        if (connected) {
          twiml.hangup();
          break;
        }

        // Return an unaccepted call to Maya.
        const studio = new URL(context.MAYA_STUDIO_WEBHOOK_URL);

        if (
          studio.protocol !== "https:" ||
          studio.hostname !== "webhooks.twilio.com"
        ) {
          throw new Error("Invalid MAYA_STUDIO_WEBHOOK_URL.");
        }

        studio.searchParams.set("FlowEvent", "return");

        twiml.redirect(
          { method: "POST" },
          studio.toString()
        );
        break;
      }

      case "start": {
        const owner = context.MAYA_OWNER_CELL;

        if (!/^\+[1-9]\d{7,14}$/.test(owner || "")) {
          throw new Error(
            "MAYA_OWNER_CELL must include + and the country code."
          );
        }

        // Validate the return URL before dialing.
        const studio = new URL(context.MAYA_STUDIO_WEBHOOK_URL);

        if (
          studio.protocol !== "https:" ||
          studio.hostname !== "webhooks.twilio.com"
        ) {
          throw new Error("Invalid MAYA_STUDIO_WEBHOOK_URL.");
        }

        const dial = twiml.dial({
          callerId: "+13149472537",
          answerOnBridge: true,
          timeout: 15,
          action: stepUrl("result"),
          method: "POST"
        });

        dial.number(
          {
            url: stepUrl("screen"),
            method: "POST"
          },
          owner
        );
        break;
      }

      default:
        twiml.hangup();
    }

    return callback(null, twiml);
  } catch (error) {
    return callback(error);
  }
};
