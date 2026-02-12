addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  if (request.method !== 'POST') {
    return new Response('', {status: 405})
  }
  let reqBody
  try {
    reqBody = await request.json()
  } catch (e) {
    return new Response('', {status: 400})
  }
  if (reqBody.event_type === 'event_verification' && reqBody.event && reqBody.event.seatalk_challenge) {
    const seatalk_challenge = reqBody.event.seatalk_challenge
    const respBody = JSON.stringify({ seatalk_challenge })
    return new Response(respBody, {
      status: 200,
      headers: {'Content-Type': 'application/json'}
    })
  }
  return new Response('', {status: 200})
}
