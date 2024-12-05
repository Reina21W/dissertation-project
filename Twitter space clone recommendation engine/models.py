from py2neo import Graph, Node, NodeMatcher, Relationship
from datetime import datetime
import uuid
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class Database:
    def __init__(self, uri, user, password):
        self.graph = Graph(uri, auth=(user, password))
        self.matcher = NodeMatcher(self.graph)

    def create_user(self, username, password, email):
        created_at = datetime.now().isoformat()
        user_node = Node("User", username=username, password=password,
                         email=email, created_at=created_at)
        self.graph.create(user_node)

    def user_exists(self, username):
        return self.matcher.match("User", username=username).first() is not None

    def get_user(self, username):
        user_node = self.matcher.match("User", username=username).first()
        if user_node:
            return {
                'username': user_node['username'],
                'password': user_node['password'],
                'email': user_node['email']
            }
        return None

    def find_user(self, username):
        user = self.graph.nodes.match("User", username=username).first()
        return user

    def add_post(self, username, text, tags):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = Node(
            "Post",
            id=str(uuid.uuid4()),
            text=text,
            timestamp=int(datetime.now().timestamp()),
            date=datetime.now().strftime("%Y-%m-%d")
        )


        query = """
        MATCH (u:User)-[r:PUBLISHED_ON]->(p:Post)
        WHERE u.username = $username
        RETURN r, p
        ORDER BY p.timestamp DESC
        LIMIT 1
        """
        result = self.graph.run(query, username=username).data()


        rel = Relationship(user, "PUBLISHED_ON", post, status=True,
                           date=datetime.now().strftime("%Y-%m-%d"))
        self.graph.create(rel)
        self.graph.create(Relationship(post, "BY", user))



        for tag in tags:
            topic_name = tag.strip("#")
            topic = self.graph.nodes.match("Topic", name=topic_name).first()
            if not topic:
                topic = Node("Topic", name=topic_name)
                self.graph.create(topic)
            self.graph.create(Relationship(post, "HAS_TOPIC", topic))

    def get_all_posts(self):
        query = """
        MATCH (u:User)-[:PUBLISHED_ON]->(p:Post)
        OPTIONAL MATCH (p)-[:HAS_TOPIC]->(t:Topic)
        WITH u, p, COLLECT(t.name) AS topics
        ORDER BY p.timestamp DESC
        RETURN u.username AS username, p.id AS post_id, p.text AS text, p.date AS date, topics
        """
        return self.graph.run(query).data()

    def get_user_posts(self, username):
        query = """
        MATCH (u:User {username: $username})-[:PUBLISHED_ON]->(p:Post)
        RETURN p.id AS post_id, p.text AS text, p.date AS date
        ORDER BY p.timestamp DESC
        """
        return self.graph.run(query, username=username).data()

    def add_comment(self, username, post_id, comment_text):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")

        comment = Node(
            "Comment",
            id=str(uuid.uuid4()),
            text=comment_text,
            timestamp=int(datetime.now().timestamp()),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        self.graph.create(comment)
        self.graph.create(Relationship(user, "COMMENTED", comment))
        self.graph.create(Relationship(comment, "ON", post))

    def get_comments(self, post_id):
        query = """
        MATCH (c:Comment)-[:ON]->(p:Post {id: $post_id})
        MATCH (u:User)-[:COMMENTED]->(c)
        RETURN u.username AS username, c.text AS text, c.date AS date
        ORDER BY c.timestamp ASC
        """
        return self.graph.run(query, post_id=post_id).data()

    def like_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")

        self.graph.create(Relationship(user, "LIKES", post))

    def unlike_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")

        query = """
        MATCH (u:User)-[r:LIKES]->(p:Post)
        WHERE u.username = $username AND p.id = $post_id
        DELETE r
        """
        self.graph.run(query, username=username, post_id=post_id)

    def like_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")

        self.graph.create(Relationship(user, "LIKES", post))

    def unlike_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")

        query = """
               MATCH (u:User)-[r:LIKES]->(p:Post)
               WHERE u.username = $username AND p.id = $post_id
               DELETE r
               """
        self.graph.run(query, username=username, post_id=post_id)

    def follow_user(self, username, target_username):
        user = self.find_user(username)
        target_user = self.find_user(target_username)
        if not user or not target_user:
            raise ValueError("User not found")
        self.graph.create(Relationship(user, "FOLLOWS", target_user))

    def unfollow_user(self, username, target_username):
        user = self.find_user(username)
        target_user = self.find_user(target_username)
        if not user or not target_user:
            raise ValueError("User not found")

        query = """
        MATCH (u:User)-[r:FOLLOWS]->(t:User)
        WHERE u.username = $username AND t.username = $target_username
        DELETE r
        """
        self.graph.run(query, username=username, target_username=target_username)

    def get_user(self, username):
        user_node = self.find_user(username)
        if user_node:
            return {
                'username': user_node['username'],
                'email': user_node['email'],
                'password': user_node['password'],
                'created_at': user_node['created_at']
            }
        return None

    def get_following(self, username):
        query = """
        MATCH (u:User)-[:FOLLOWS]->(f:User)
        WHERE u.username = $username
        RETURN f.username AS username
        """
        return [record["username"] for record in self.graph.run(query, username=username)]

    def get_followers(self, username):
        query = """
        MATCH (u:User)<-[:FOLLOWS]-(f:User)
        WHERE u.username = $username
        RETURN f.username AS username
        """
        return [record["username"] for record in self.graph.run(query, username=username)]

    def repost_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        original_post = self.graph.nodes.match("Post", id=post_id).first()
        if not original_post:
            raise ValueError("Post not found")

        repost = Node(
            "Post",
            id=str(uuid.uuid4()),
            text=original_post["text"],
            timestamp=int(datetime.now().timestamp()),
            date=datetime.now().strftime("%Y-%m-%d")
        )

        self.graph.create(repost)
        self.graph.create(Relationship(user, "REPOSTED", repost))
        self.graph.create(Relationship(repost, "REPOST_OF", original_post))

    def get_user_reposts(self, username):
        query = """
        MATCH (u:User {username: $username})-[:REPOSTED]->(r:Repost)-[:REPOST_OF]->(p:Post)<-[:BY]-(original_user:User)
        RETURN p.id AS post_id, p.text AS text, p.date AS original_date, r.date AS repost_date, original_user.username AS original_username
        ORDER BY r.timestamp DESC
        """
        return self.graph.run(query, username=username).data()

    def is_following(self, username, target_username):
        query = """
        MATCH (u:User)-[:FOLLOWS]->(f:User)
        WHERE u.username = $username AND f.username = $target_username
        RETURN COUNT(*) > 0 AS is_following
        """
        result = self.graph.run(query, username=username, target_username=target_username).evaluate()
        return result

    def create_space(self, username, space_name, space_description, topics):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        space = Node(
            "Space",
            id=str(uuid.uuid4()),
            name=space_name,
            description=space_description,
            created_at=datetime.now().isoformat()
        )

        self.graph.create(space)
        self.graph.create(Relationship(user, "HOSTS", space))

        for topic_name in topics:
            topic = self.graph.nodes.match("Topic", name=topic_name).first()
            if not topic:
                topic = Node("Topic", name=topic_name)
                self.graph.create(topic)
            self.graph.create(Relationship(space, "HAS_TOPIC", topic))

    def get_all_spaces(self, username):
        query = """
        MATCH (s:Space)<-[:HOSTS]-(u:User)
        OPTIONAL MATCH (s)<-[:JOINED_AS]-(j:User)
        RETURN s.id AS id, s.name AS name, s.description AS description, s.created_at AS created_at, 
               u.username AS host, s.status AS status, COLLECT(j.username) AS members, COUNT(j) AS member_count,
               EXISTS((:User {username: $username})-[:JOINED_AS]->(s)) AS is_member,
               CASE WHEN u.username = $username THEN True ELSE False END AS is_host
        ORDER BY s.created_at DESC
        """
        return self.graph.run(query, username=username).data()

    def get_all_topics(self):
        query = """
        MATCH (t:Topic)
        RETURN t.name AS name
        ORDER BY t.name
        """
        return [record["name"] for record in self.graph.run(query)]

    def is_member_of_space(self, username, space_id):
        query = """
        MATCH (u:User {username: $username})-[:JOINED_AS]->(s:Space {id: $space_id})
        RETURN u
        """
        return self.graph.run(query, username=username, space_id=space_id).evaluate() is not None

    def delete_space(self, username, space_id):

        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")


        space = self.graph.nodes.match("Space", id=space_id).first()
        if not space:
            raise ValueError("Space not found")

        # debugging information
        print(f"Attempting to delete space with id: {space_id} for user: {username}")

        # Check if the user is the host of the space
        query = """
        MATCH (u:User {username: $username})-[r:HOSTS]->(s:Space {id: $space_id})
        RETURN r
        """
        result = self.graph.run(query, username=username, space_id=space_id).evaluate()

        # Output debugging information for query results
        print(f"HOSTS relationship query result: {result}")

        # If no HOSTS relationship is found, an exception is thrown
        if result is None:
            raise ValueError(f"User {username} is not the host of space with id: {space_id}")


        query = """
        MATCH (s:Space {id: $space_id})
        DETACH DELETE s
        """
        self.graph.run(query, space_id=space_id)
        print(f"Space with id: {space_id} successfully deleted")

    def delete_post(self, username, post_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        post = self.graph.nodes.match("Post", id=post_id).first()
        if not post:
            raise ValueError("Post not found")


        query = """
        MATCH (u:User)-[r:PUBLISHED_ON]->(p:Post)
        WHERE u.username = $username AND p.id = $post_id
        RETURN r
        """
        result = self.graph.run(query, username=username, post_id=post_id).data()

        if not result:
            raise ValueError("User is not the author of this post")


        query = """
        MATCH (p:Post {id: $post_id})
        DETACH DELETE p
        """
        self.graph.run(query, post_id=post_id)

    def delete_comment(self, username, comment_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        comment = self.graph.nodes.match("Comment", id=comment_id).first()
        if not comment:
            raise ValueError("Comment not found")

        query = """
        MATCH (u:User)-[r:COMMENTED]->(c:Comment)
        WHERE u.username = $username AND c.id = $comment_id
        RETURN r
        """
        result = self.graph.run(query, username=username, comment_id=comment_id).data()

        if not result:
            raise ValueError("User is not the author of this comment")

        query = """
        MATCH (c:Comment {id: $comment_id})
        DETACH DELETE c
        """
        self.graph.run(query, comment_id=comment_id)

    def join_space(self, username, space_id, role):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        space = self.graph.nodes.match("Space", id=space_id).first()
        if not space:
            raise ValueError("Space not found")

        joined_at = datetime.now().isoformat()
        self.graph.create(Relationship(user, "JOINED_AS", space, role=role,
                                       joined_at=joined_at))

    def leave_space(self, username, space_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        space = self.graph.nodes.match("Space", id=space_id).first()
        if not space:
            raise ValueError("Space not found")

        query = """
        MATCH (u:User)-[r:JOINED_AS]->(s:Space)
        WHERE u.username = $username AND s.id = $space_id
        RETURN r
        """
        relationship = self.graph.run(query, username=username,
                                      space_id=space_id).evaluate()

        if relationship:
            joined_at = datetime.fromisoformat(relationship["joined_at"])
            left_at = datetime.now()
            duration = (left_at - joined_at).total_seconds()  # Calculate duration in seconds

            self.graph.separate(relationship)
            self.graph.create(
                Relationship(user, "LEFT_AS", space, role=relationship["role"],
                             joined_at=joined_at.isoformat(),
                             left_at=left_at.isoformat(), duration=duration))

    def end_space(self, username, space_id):
        user = self.find_user(username)
        if not user:
            raise ValueError("User not found")

        space = self.graph.nodes.match("Space", id=space_id).first()
        if not space:
            raise ValueError("Space not found")


        space_created_at = space["created_at"]
        if not space_created_at:
            raise ValueError(f"Space {space_id} does not have a valid created_at time")

        print(f"Ending space with id: {space_id} for user: {username}. "
              f"Space created at: {space_created_at}")


        query = """
        MATCH (u:User {username: $username})-[r:HOSTS]->(s:Space {id: $space_id})
        RETURN r, u.username AS host_username
        """
        result = self.graph.run(query, username=username, space_id=space_id).data()

        if not result:
            raise ValueError(f"User {username} is not the host of space with id: {space_id}")


        query = """
        MATCH (u:User {username: $username})-[r:HOSTS]->(s:Space {id: $space_id})
        WITH r, s, datetime($created_at) AS created_at_dt
        SET r.left_at = timestamp(),
            r.duration = (timestamp() - datetime($created_at).epochMillis)/3600000,  // 转换为小时
            s.status = "ended"
        RETURN r.duration AS duration
        """
        duration_result = self.graph.run(query, username=username, space_id=space_id,
                                         created_at=space_created_at).data()


        print(f"Host duration for {username}: {duration_result}")


        query = """
        MATCH (u:User)-[r:JOINED_AS]->(s:Space {id: $space_id})
        WHERE r.joined_at IS NOT NULL
        WITH r, datetime(r.joined_at) AS joined_at_dt
        SET r.left_at = timestamp(),
            r.duration = (timestamp() - datetime(r.joined_at).epochMillis)/3600000  // 转换为小时
        RETURN r.duration AS duration
        """
        member_duration_result = self.graph.run(query, space_id=space_id).data()


        print(f"Member duration for space {space_id}: {member_duration_result}")


        query = """
        MATCH (s:Space {id: $space_id})
        SET s.status = "ended"
        """
        self.graph.run(query, space_id=space_id)

        print(f"Space with id {space_id} ended successfully by {username}.")

    def get_user_space_durations(self, username):
        query = """
        MATCH (u:User {username: $username})-[r]->(s:Space)
        WHERE type(r) IN ['JOINED_AS', 'HOSTS', 'LEFT_AS']
        RETURN s.name AS space_name, r.role AS role, 
               CASE 
                   WHEN r.left_at IS NULL THEN (timestamp() - r.joined_at)/3600
                   ELSE r.duration
               END AS duration, 
               r.joined_at AS joined_at, 
               r.left_at AS left_at, 
               type(r) AS relationship_type
        """
        return self.graph.run(query, username=username).data()

    def get_space_vectors(self):
        query = """
           MATCH (s:Space)-[:HAS_TOPIC]->(t:Topic)
           RETURN s.id AS id, s.name AS name, COLLECT(t.name) AS topics
           """
        spaces = self.graph.run(query).data()

        all_topics = {record['name'] for record in
                      self.graph.run("MATCH (t:Topic) RETURN t.name AS name").data()}

        space_vectors = []
        for space in spaces:
            vector = {topic: 0 for topic in all_topics}
            for topic in space['topics']:
                vector[topic] = 1
            space_vectors.append({'id': space['id'], 'name': space['name'], 'vector': vector})

        return space_vectors

    def calculate_user_topic_vector(self, username):
        vector = {}
        query = "MATCH (t:Topic) RETURN t.name AS topic"
        result = self.graph.run(query).data()
        for record in result:
            vector[record['topic']] = 0


        query = """
        MATCH (u:User {username: $username})-[j:JOINED_AS]->(s:Space)-[:HAS_TOPIC]->(t:Topic)
        WITH t.name AS topic, j.role AS role, j.joined_at AS joined_at, j.left_at AS left_at, 
        j.duration AS duration, s.status AS space_status
        RETURN topic, role, joined_at, left_at, duration, space_status
        """
        result = self.graph.run(query, username=username).data()

        role_weight = {"listener": 1, "speaker": 1.5, "moderator": 1.7, "host": 2}

        for record in result:
            topic = record['topic']
            role = record['role']


            if record['space_status'] == 'ended':
                duration = record['duration']
            else:
                joined_at = datetime.strptime(record['joined_at'], "%Y-%m-%dT%H:%M:%S.%f")
                duration = (datetime.now() - joined_at).total_seconds() / 3600

            weight = role_weight.get(role, 1) * duration
            vector[topic] += weight


        query = """
            MATCH (u:User {username: $username})-[:PUBLISHED_ON]->(p:Post)-[:HAS_TOPIC]->(t:Topic)
            RETURN t.name AS topic, COUNT(p) AS post_count
            """
        result = self.graph.run(query, username=username).data()
        for record in result:
            topic = record['topic']
            vector[topic] += record['post_count'] * 3  # Each posts +3 points

        query = """
            MATCH (u:User {username: $username})-[:REPOSTED]->(p:Post)-[:HAS_TOPIC]->(t:Topic)
            RETURN t.name AS topic, COUNT(p) AS repost_count
            """
        result = self.graph.run(query, username=username).data()
        for record in result:
            topic = record['topic']
            vector[topic] += record['repost_count'] * 2  # Each repost +2 points

        query = """
            MATCH (u:User {username: $username})-[:LIKES]->(p:Post)-[:HAS_TOPIC]->(t:Topic)
            RETURN t.name AS topic, COUNT(p) AS like_count
            """
        result = self.graph.run(query, username=username).data()
        for record in result:
            topic = record['topic']
            vector[topic] += record['like_count'] * 1  # each like +1 points

        return vector





    def get_user_behavior(self, username):
        query = """
        MATCH (u:User {username: $username})
        OPTIONAL MATCH (u)-[:PUBLISHED_ON]->(p:Post)    
        OPTIONAL MATCH (u)-[:REPOSTED]->(r:Post)        
        OPTIONAL MATCH (u)-[:LIKES]->(liked:Post)       
        OPTIONAL MATCH (u)-[:JOINED_AS]->(s:Space)      
        RETURN COUNT(DISTINCT p) AS posts_count, 
               COUNT(DISTINCT r) AS reposts_count, 
               COUNT(DISTINCT liked) AS likes_count,
               COUNT(DISTINCT s) AS spaces_count
        """
        result = self.graph.run(query, username=username).data()


        if result and result[0]:
            return {
                'posts_count': result[0]['posts_count'],
                'reposts_count': result[0]['reposts_count'],
                'likes_count': result[0]['likes_count'],
                'spaces_count': result[0]['spaces_count']
            }
        return None

    def get_user_following_count(self, username):
        query = """
        MATCH (u:User {username: $username})-[:FOLLOWS]->(f:User)
        RETURN COUNT(DISTINCT f) AS following_count
        """
        result = self.graph.run(query, username=username).data()


        if result and result[0]:
            return result[0]['following_count']
        return 0

    def get_latest_spaces(self, top_n=5):
        query = """
        MATCH (s:Space)
        RETURN s.id AS id, s.name AS name, s.description AS description, 
        s.created_at AS created_at, 
               s.status AS status
        ORDER BY s.created_at DESC
        LIMIT $top_n
        """
        return self.graph.run(query, top_n=top_n).data()

    def get_recommendations_from_friends(self, username, top_n=5):
        query = """
        MATCH (u:User {username: $username})-[:FOLLOWS]->(friend:User)-[:JOINED_AS]->(s:Space)
        RETURN s.id AS id, s.name AS name, 
        s.description AS description, s.created_at AS created_at, 
               friend.username AS friend, s.status AS status
        ORDER BY s.created_at DESC
        LIMIT $top_n
        """
        return self.graph.run(query, username=username, top_n=top_n).data()

    def recommend_spaces_based_on_behavior(self, username, top_n=5):
        user_vector = self.calculate_user_topic_vector(username)
        space_vectors = self.get_space_vectors()

        # Check if space_vectors is empty
        if not space_vectors:
            return []

        user_vector_values = np.array([list(user_vector.values())])
        space_vectors_values = np.array([list(space['vector'].values())
                                         for space in space_vectors])


        similarities = cosine_similarity(user_vector_values, space_vectors_values)[0]
        top_indices = similarities.argsort()[-top_n:][::-1]

        recommended_spaces = []
        for index in top_indices:
            space = space_vectors[index]
            space_info = self.graph.run("""
                MATCH (s:Space {id: $space_id})<-[:HOSTS]-(u:User)
                RETURN s.id AS id, s.name AS name, s.description AS description, s.created_at AS created_at, 
                       s.status AS status, u.username AS host
            """, space_id=space['id']).data()[0]

            recommended_spaces.append({
                'id': space_info['id'],
                'name': space_info['name'],
                'description': space_info.get('description', 'No description available'),
                'host': space_info.get('host', 'Unknown'),
                'created_at': space_info.get('created_at', 'Unknown'),
                'status': space_info.get('status', 'alive')
            })

        return recommended_spaces

    def recommend_spaces(self, username, top_n=5):
        # Get user behavioural data and number of followers
        user_behavior = self.get_user_behavior(username)
        following_count = self.get_user_following_count(username)

        # Determine user behaviour or relationship of interest
        if user_behavior['posts_count'] == 0 and user_behavior['reposts_count'] == 0 and user_behavior['likes_count'] == 0 and user_behavior['spaces_count'] == 0 and following_count == 0:
            # New users, with no behaviour or following anyone, return to the space of the latest release
            return self.get_latest_spaces(top_n=top_n)

        elif user_behavior['posts_count'] == 0 and user_behavior['reposts_count'] == 0 and user_behavior['likes_count'] == 0 and user_behavior['spaces_count'] == 0 and following_count > 0:
        # Users with followers but no behaviours, recommending spaces that friends have participated in
            return self.get_recommendations_from_friends(username, top_n=top_n)
        else:
        # Users with behavioural data, using behaviour-based recommendation logic
            return self.recommend_spaces_based_on_behavior(username, top_n)

        # Test Node similarity
        # return self.recommend_spaces_using_similarity(username, top_n)

    # Neo4j Node similarity
    # def recommend_spaces_using_similarity(self, username, top_n=5):
    #
    #     create_graph_query = """
    #     CALL gds.graph.project(
    #       'userSpaceGraph',
    #       ['User', 'Space'],
    #       {
    #         JOINED_AS: {
    #           type: 'JOINED_AS',orientation: 'UNDIRECTED'
    #         },
    #          HOSTS: {
    #           type: 'HOSTS',orientation: 'UNDIRECTED'
    #         }
    #       }
    #     )
    #     """
    #     self.graph.run(create_graph_query)
    #
    #
    #     similarity_query = """
    #     CALL gds.nodeSimilarity.stream('userSpaceGraph')
    #     YIELD node1, node2, similarity
    #     RETURN gds.util.asNode(node1).username AS user1,
    #            gds.util.asNode(node2).username AS user2,
    #            similarity
    #     ORDER BY similarity DESC
    #     """
    #
    #
    #     results = self.graph.run(similarity_query).data()
    #
    #
    #     similar_users = [record['user2'] for record in results if record['user1'] == username]
    #
    #     if not similar_users:
    #         return []
    #
    #
    #     query = """
    #     MATCH (u:User)-[:JOINED_AS]->(s:Space)
    #     WHERE u.username IN $similar_users
    #     RETURN s.id AS id, s.name AS name, s.description AS description,
    #            s.created_at AS created_at,
    #            u.username AS host
    #     ORDER BY s.created_at DESC
    #     LIMIT $top_n
    #     """
    #
    #     recommended_spaces = self.graph.run(query, similar_users=similar_users, top_n=top_n).data()
    #
    #     return recommended_spaces




