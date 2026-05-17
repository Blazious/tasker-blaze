import cloudinary
from django.conf import settings
from rest_framework import serializers

from .models import Bid, Task, TaskCategory


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = ("id", "name", "slug", "icon_name", "description", "is_active")


class BidSerializer(serializers.ModelSerializer):
    tasker = serializers.StringRelatedField(read_only=True)
    tasker_id = serializers.IntegerField(source="tasker.id", read_only=True)
    tasker_full_name = serializers.CharField(source="tasker.full_name", read_only=True)
    tasker_availability_status = serializers.CharField(
        source="tasker.availability_status",
        read_only=True,
    )
    tasker_availability_note = serializers.CharField(
        source="tasker.availability_note",
        read_only=True,
    )
    task_title = serializers.CharField(source="task.title", read_only=True)
    task_status = serializers.CharField(source="task.status", read_only=True)

    class Meta:
        model = Bid
        fields = (
            "id",
            "task",
            "task_title",
            "task_status",
            "tasker",
            "tasker_id",
            "tasker_full_name",
            "tasker_availability_status",
            "tasker_availability_note",
            "amount",
            "message",
            "status",
            "created_at",
        )
        read_only_fields = (
            "id",
            "task",
            "task_title",
            "task_status",
            "tasker",
            "tasker_id",
            "tasker_full_name",
            "tasker_availability_status",
            "tasker_availability_note",
            "status",
            "created_at",
        )


class TaskSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    client_id = serializers.IntegerField(source="client.id", read_only=True)
    category_detail = TaskCategorySerializer(source="category", read_only=True)
    assigned_tasker = serializers.StringRelatedField(read_only=True)
    assigned_tasker_id = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)
    bid_count = serializers.SerializerMethodField()
    bids = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_provider = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "client",
            "client_id",
            "title",
            "description",
            "category",
            "category_detail",
            "budget_min",
            "budget_max",
            "location_landmark",
            "location_notes",
            "location_latitude",
            "location_longitude",
            "task_photo",
            "requires_home_visit",
            "preferred_tasker_gender",
            "status",
            "created_at",
            "updated_at",
            "assigned_tasker",
            "assigned_tasker_id",
            "assigned_at",
            "completed_at",
            "schedule_type",
            "scheduled_for",
            "deadline",
            "is_open",
            "bid_count",
            "bids",
            "payment_status",
            "payment_provider",
            "payment_amount",
        )
        read_only_fields = (
            "id",
            "client",
            "client_id",
            "status",
            "created_at",
            "updated_at",
            "assigned_tasker",
            "assigned_tasker_id",
            "assigned_at",
            "completed_at",
            "is_open",
            "bid_count",
            "bids",
            "payment_status",
            "payment_provider",
            "payment_amount",
        )

    def get_bid_count(self, obj):
        return obj.bids.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        can_view_notes = (
            user
            and user.is_authenticated
            and (instance.client_id == user.id or instance.assigned_tasker_id == user.id)
        )
        if not can_view_notes:
            data["location_notes"] = ""
            data["location_latitude"] = None
            data["location_longitude"] = None
        return data

    def get_bids(self, obj):
        request = self.context.get("request")
        if not request or request.user != obj.client:
            return []
        return BidSerializer(obj.bids.select_related("tasker"), many=True).data

    def get_assigned_tasker_id(self, obj):
        return obj.assigned_tasker_id

    def get_payment_status(self, obj):
        transaction = getattr(obj, "transaction", None)
        return transaction.status if transaction else None

    def get_payment_provider(self, obj):
        transaction = getattr(obj, "transaction", None)
        return transaction.payment_provider if transaction else None

    def get_payment_amount(self, obj):
        transaction = getattr(obj, "transaction", None)
        return str(transaction.total_charged) if transaction else None

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if request and request.method == "POST":
            if not user or not user.is_authenticated:
                raise serializers.ValidationError("Authentication is required.")
            if not user.is_verified:
                raise serializers.ValidationError("Only verified users can post tasks.")

        budget_min = attrs.get("budget_min", getattr(self.instance, "budget_min", None))
        budget_max = attrs.get("budget_max", getattr(self.instance, "budget_max", None))
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            raise serializers.ValidationError(
                {"budget_max": "Maximum budget must be greater than minimum budget."}
            )

        location_landmark = attrs.get(
            "location_landmark",
            getattr(self.instance, "location_landmark", None),
        )
        location_notes = attrs.get(
            "location_notes",
            getattr(self.instance, "location_notes", ""),
        )
        if location_landmark == "Other (specify in notes)" and not location_notes:
            raise serializers.ValidationError(
                {"location_notes": "Please specify the location in notes."}
            )

        schedule_type = attrs.get(
            "schedule_type",
            getattr(self.instance, "schedule_type", Task.ScheduleType.ASAP),
        )
        scheduled_for = attrs.get(
            "scheduled_for",
            getattr(self.instance, "scheduled_for", None),
        )
        deadline = attrs.get("deadline", getattr(self.instance, "deadline", None))
        if schedule_type == Task.ScheduleType.SCHEDULED:
            if not scheduled_for:
                raise serializers.ValidationError(
                    {"scheduled_for": "Choose when this scheduled task should start."}
                )
            from django.utils import timezone

            if scheduled_for <= timezone.now():
                raise serializers.ValidationError(
                    {"scheduled_for": "Scheduled tasks must be set for a future time."}
                )
        if deadline and scheduled_for and deadline < scheduled_for:
            raise serializers.ValidationError(
                {"deadline": "Deadline cannot be before the scheduled start time."}
            )

        return attrs

    def create(self, validated_data):
        if (
            settings.DEBUG
            and validated_data.get("task_photo")
            and not cloudinary.config().api_key
        ):
            validated_data.pop("task_photo", None)
        return Task.objects.create(client=self.context["request"].user, **validated_data)


class BidCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ("id", "amount", "message", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        task = self.context["task"]
        user = request.user

        if not user.is_tasker_active:
            raise serializers.ValidationError(
                "Activate tasker mode before placing bids."
            )
        from apps.payments.billing import overdue_balance

        overdue = overdue_balance(user)
        if overdue > 0:
            raise serializers.ValidationError(
                f"You have KES {overdue} overdue platform fees. Please settle your invoice before placing new bids."
            )
        if task.client_id == user.id:
            raise serializers.ValidationError("A tasker cannot bid on their own task.")
        if task.status != Task.Status.OPEN:
            raise serializers.ValidationError("Bids can only be placed on open tasks.")
        if Bid.objects.filter(task=task, tasker=user).exists():
            raise serializers.ValidationError("You have already placed a bid on this task.")

        return attrs

    def create(self, validated_data):
        return Bid.objects.create(
            task=self.context["task"],
            tasker=self.context["request"].user,
            **validated_data,
        )
